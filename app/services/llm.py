import json
import logging
import re
import requests
from typing import List

from loguru import logger
from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from app.config import config

_max_retries = 5
_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_DEPRECATED_GEMINI_MODELS = {"gemini-pro", "gemini-1.0-pro"}
MIN_SCRIPT_PARAGRAPH_NUMBER = 1
MAX_SCRIPT_PARAGRAPH_NUMBER = 10
MAX_SCRIPT_PROMPT_LENGTH = 2000
MAX_SCRIPT_SYSTEM_PROMPT_LENGTH = 8000

DEFAULT_SCRIPT_SYSTEM_PROMPT = """
# Role: Video Script Generator

## Goals:
Generate a script for a video, depending on the subject of the video.

## Constrains:
1. the script is to be returned as a string with the specified number of paragraphs.
2. do not under any circumstance reference this prompt in your response.
3. get straight to the point, don't start with unnecessary things like, "welcome to this video".
4. you must not include any type of markdown or formatting in the script, never use a title.
5. only return the raw content of the script.
6. do not include "voiceover", "narrator" or similar indicators of what should be spoken at the beginning of each paragraph or line.
7. you must not mention the prompt, or anything about the script itself. also, never talk about the amount of paragraphs or lines. just write the script.
8. respond in the same language as the video subject.
""".strip()

VIRAL_PROMPT_TEMPLATES = {
    "viral_shorts": """
# Role: Video Script Generator - Viral Shorts Mode
## Objective:
Generate a high-retention, extremely engaging short video script designed to go viral.
## Key Rules:
- Hook the user in the first 2 seconds with a shocking statement, a bold claim, or a highly intriguing question.
- Pacing must be fast, rhythmic, and high-energy. Keep sentences very short and punchy.
- Target platform is: {target_platform}.
- Tone of delivery: {emotional_tone}.
{trend_info}
- End with a strong Call to Action (CTA) or a loopable question that naturally flows back to the start.
- Do not include any brackets, narrator directions, voiceover labels, or title lines.
- Write the raw script to be spoken.
- Respond in the same language as the video subject.
""".strip(),

    "motivational": """
# Role: Video Script Generator - Motivational Mode
## Objective:
Generate an emotionally resonant, deeply inspiring, and powerful motivational script.
## Key Rules:
- Start with a deep truth, a hard-hitting question, or a core struggle that everyone experiences.
- Pacing should feel deliberate, dramatic, and emotionally building. Use powerful verbs and contrast.
- Target platform is: {target_platform}.
- Tone of delivery: {emotional_tone}.
{trend_info}
- Inspire action, self-reflection, and a sense of triumph in the viewer.
- Do not include any brackets, narrator directions, voiceover labels, or title lines.
- Write the raw script to be spoken.
- Respond in the same language as the video subject.
""".strip(),

    "educational": """
# Role: Video Script Generator - Educational Mode
## Objective:
Generate an informative, clear, and fascinating educational script.
## Key Rules:
- Start with a "Did you know?" style hook, a mind-blowing fact, or a counter-intuitive truth.
- Break down complex ideas into simple, mind-blowing analogies. Avoid technical jargon.
- Pacing should be informative yet engaging. Deliver high density of value.
- Target platform is: {target_platform}.
- Tone of delivery: {emotional_tone}.
{trend_info}
- Keep the explanation extremely clear and fun.
- Do not include any brackets, narrator directions, voiceover labels, or title lines.
- Write the raw script to be spoken.
- Respond in the same language as the video subject.
""".strip(),

    "storytelling": """
# Role: Video Script Generator - Storytelling Mode
## Objective:
Generate a narrative-driven, dramatic, and lesson-teaching storytelling script.
## Key Rules:
- Begin right in the middle of action or with a striking character detail.
- Pacing should follow a clear rising action, a climax, and a resolution.
- Target platform is: {target_platform}.
- Tone of delivery: {emotional_tone}.
{trend_info}
- Build suspense, curiosity, and emotional investment.
- Do not include any brackets, narrator directions, voiceover labels, or title lines.
- Write the raw script to be spoken.
- Respond in the same language as the video subject.
""".strip(),

    "listicle": """
# Role: Video Script Generator - Listicle Mode
## Objective:
Generate a fast-paced, highly structured list format script.
## Key Rules:
- Hook with the ultimate promise (e.g. "Here are the top 3 secrets to..." or "3 signs you are...").
- Deliver itemized points rapidly, keeping explanations concise.
- Target platform is: {target_platform}.
- Tone of delivery: {emotional_tone}.
{trend_info}
- Keep the structure clean and list-oriented. Make points stand out clearly.
- Do not include any brackets, narrator directions, voiceover labels, or title lines.
- Write the raw script to be spoken.
- Respond in the same language as the video subject.
""".strip(),

    "trending_topic": """
# Role: Video Script Generator - Trending Topic Mode
## Objective:
Generate a news-style or commentary script capitalizing on a recent viral trend or event.
## Key Rules:
- Hook by identifying the trend or event immediately.
- Offer a unique angle, critical insight, or popular perspective.
- Target platform is: {target_platform}.
- Tone of delivery: {emotional_tone}.
{trend_info}
- Maintain a timely, relevant, and engaging commentary.
- Do not include any brackets, narrator directions, voiceover labels, or title lines.
- Write the raw script to be spoken.
- Respond in the same language as the video subject.
""".strip()
}


def _normalize_text_response(content, llm_provider: str) -> str:
    # 不同 LLM SDK 在异常或被拦截场景下，可能返回 None、空字符串，
    # 甚至返回非字符串对象。这里统一做兜底校验，避免后续直接调用
    # `.replace()` 时抛出 `NoneType` 之类的属性错误。
    if content is None:
        raise ValueError(f"[{llm_provider}] returned empty text content")

    if not isinstance(content, str):
        raise TypeError(
            f"[{llm_provider}] returned non-text content: {type(content).__name__}"
        )

    content = content.strip()
    if not content:
        raise ValueError(f"[{llm_provider}] returned empty text content")

    return content.replace("\n", "")


def _extract_chat_completion_text(response, llm_provider: str) -> str:
    # OpenAI 兼容接口在异常场景下，可能返回没有 choices、
    # 或者 choices/message/content 为空的响应对象。
    # 这里统一做结构校验，避免出现 `NoneType is not subscriptable`
    # 这类底层属性访问错误。
    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError(f"[{llm_provider}] returned empty choices")

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)
    if message is None:
        raise ValueError(f"[{llm_provider}] returned empty message")

    content = getattr(message, "content", None)
    return _normalize_text_response(content, llm_provider)


def _generate_response(prompt: str, user_id: str = "global") -> str:
    try:
        content = ""
        llm_provider = config.app.get("llm_provider", "openai")
        logger.info(f"llm provider: {llm_provider}")
        if llm_provider == "g4f":
            if not config.app.get("enable_g4f", False):
                raise ValueError(
                    "g4f provider is disabled by default because it relies on "
                    "reverse-engineered third-party endpoints. Set enable_g4f=true "
                    "in config.toml only if you understand and accept the security, "
                    "reliability, and legal risks."
                )

            logger.warning(
                "g4f provider is enabled. This provider may be unstable and carries "
                "supply-chain and terms-of-service risks. Prefer official providers, "
                "OpenAI-compatible APIs, LiteLLM, Ollama, or local inference for production."
            )
            try:
                import g4f
            except ImportError as e:
                raise ValueError(
                    "g4f package is not installed by default. Install the optional "
                    "dependency with `uv sync --extra g4f` only if you understand "
                    "and accept the provider risks."
                ) from e

            model_name = config.app.get("g4f_model_name", "")
            if not model_name:
                model_name = "gpt-3.5-turbo-16k-0613"
            content = g4f.ChatCompletion.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
        else:
            api_version = ""  # for azure
            if llm_provider == "moonshot":
                api_key = config.app.get("moonshot_api_key")
                model_name = config.app.get("moonshot_model_name")
                base_url = "https://api.moonshot.cn/v1"
            elif llm_provider == "ollama":
                # api_key = config.app.get("openai_api_key")
                api_key = "ollama"  # any string works but you are required to have one
                model_name = config.app.get("ollama_model_name")
                base_url = config.app.get("ollama_base_url", "")
                if not base_url:
                    base_url = config.get_default_ollama_base_url()
            elif llm_provider == "openai":
                api_key = config.app.get("openai_api_key")
                model_name = config.app.get("openai_model_name")
                base_url = config.app.get("openai_base_url", "")
                if not base_url:
                    base_url = "https://api.openai.com/v1"
            elif llm_provider == "aihubmix":
                api_key = config.app.get("aihubmix_api_key")
                model_name = config.app.get("aihubmix_model_name")
                base_url = config.app.get("aihubmix_base_url", "")
                # AIHubMix 兼容 OpenAI Chat Completions 协议。这里使用独立
                # provider 保存合作方的默认网关和推荐模型，避免把推广链接、
                # 默认模型等合作配置混进普通 OpenAI provider，影响现有用户。
                if not base_url:
                    base_url = "https://aihubmix.com/v1"
                if not model_name:
                    model_name = "gpt-5.4-mini"
            elif llm_provider == "oneapi":
                api_key = config.app.get("oneapi_api_key")
                model_name = config.app.get("oneapi_model_name")
                base_url = config.app.get("oneapi_base_url", "")
            elif llm_provider == "azure":
                api_key = config.app.get("azure_api_key")
                model_name = config.app.get("azure_model_name")
                base_url = config.app.get("azure_base_url", "")
                api_version = config.app.get("azure_api_version", "2024-02-15-preview")
            elif llm_provider == "gemini":
                from app.services import db
                api_key = db.get_setting("gemini_api_key", user_id=user_id) or config.app.get("gemini_api_key")
                if not api_key:
                    for i in range(2, 6):
                        k = db.get_setting(f"gemini_api_key_{i}", user_id=user_id)
                        if k:
                            api_key = k
                            break
                model_name = db.get_setting("gemini_model_name", user_id=user_id) or config.app.get("gemini_model_name")
                base_url = db.get_setting("gemini_base_url", user_id=user_id) or config.app.get("gemini_base_url", "")
                # Gemini 旧模型名已经陆续下线，这里自动兼容历史配置，
                # 避免用户沿用旧值时直接收到 404。
                if not model_name:
                    model_name = _DEFAULT_GEMINI_MODEL
                elif model_name in _DEPRECATED_GEMINI_MODELS:
                    logger.warning(
                        f"gemini model '{model_name}' is deprecated, fallback to '{_DEFAULT_GEMINI_MODEL}'"
                    )
                    model_name = _DEFAULT_GEMINI_MODEL
            elif llm_provider == "grok":
                api_key = config.app.get("grok_api_key")
                model_name = config.app.get("grok_model_name")
                base_url = config.app.get("grok_base_url", "")
                if not base_url:
                    base_url = "https://api.x.ai/v1"
            elif llm_provider == "qwen":
                api_key = config.app.get("qwen_api_key")
                model_name = config.app.get("qwen_model_name")
                base_url = "***"
            elif llm_provider == "cloudflare":
                api_key = config.app.get("cloudflare_api_key")
                model_name = config.app.get("cloudflare_model_name")
                account_id = config.app.get("cloudflare_account_id")
                base_url = "***"
            elif llm_provider == "minimax":
                api_key = config.app.get("minimax_api_key")
                model_name = config.app.get("minimax_model_name")
                base_url = config.app.get("minimax_base_url", "")
                if not base_url:
                    base_url = "https://api.minimax.io/v1"
            elif llm_provider == "mimo":
                api_key = config.app.get("mimo_api_key")
                model_name = config.app.get("mimo_model_name")
                base_url = config.app.get("mimo_base_url", "")
                # Xiaomi MiMo 官方文档说明其兼容 OpenAI Chat Completions 协议。
                # 这里使用独立 provider 保存默认地址和模型名，用户不用把 MiMo
                # 当作 OpenAI 自定义 base_url 配置，也便于后续继续接入 MiMo
                # 多模态或 TTS 能力时保持边界清晰。
                if not base_url:
                    base_url = "https://api.xiaomimimo.com/v1"
                if not model_name:
                    model_name = "mimo-v2.5-pro"
            elif llm_provider == "deepseek":
                api_key = config.app.get("deepseek_api_key")
                model_name = config.app.get("deepseek_model_name")
                base_url = config.app.get("deepseek_base_url")
                if not base_url:
                    base_url = "https://api.deepseek.com"
            elif llm_provider == "modelscope":
                api_key = config.app.get("modelscope_api_key")
                model_name = config.app.get("modelscope_model_name")
                base_url = config.app.get("modelscope_base_url")
                if not base_url:
                    base_url = "https://api-inference.modelscope.cn/v1/"
            elif llm_provider == "ernie":
                api_key = config.app.get("ernie_api_key")
                secret_key = config.app.get("ernie_secret_key")
                base_url = config.app.get("ernie_base_url")
                model_name = "***"
                if not secret_key:
                    raise ValueError(
                        f"{llm_provider}: secret_key is not set, please set it in the config.toml file."
                    )
            elif llm_provider == "pollinations":
                try:
                    base_url = config.app.get("pollinations_base_url", "")
                    if not base_url:
                        base_url = "https://text.pollinations.ai/openai"
                    model_name = config.app.get("pollinations_model_name", "openai-fast")
                   
                    # Prepare the payload
                    payload = {
                        "model": model_name,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "seed": 101  # Optional but helps with reproducibility
                    }
                    
                    # Optional parameters if configured
                    if config.app.get("pollinations_private"):
                        payload["private"] = True
                    if config.app.get("pollinations_referrer"):
                        payload["referrer"] = config.app.get("pollinations_referrer")
                    
                    headers = {
                        "Content-Type": "application/json"
                    }
                    
                    # Make the API request
                    response = requests.post(base_url, headers=headers, json=payload)
                    response.raise_for_status()
                    result = response.json()
                    
                    if result and "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return _normalize_text_response(content, llm_provider)
                    else:
                        raise Exception(f"[{llm_provider}] returned an invalid response format")
                        
                except requests.exceptions.RequestException as e:
                    raise Exception(f"[{llm_provider}] request failed: {str(e)}")
                except Exception as e:
                    raise Exception(f"[{llm_provider}] error: {str(e)}")

            elif llm_provider == "litellm":
                model_name = config.app.get("litellm_model_name")

            if llm_provider not in ["pollinations", "ollama", "litellm"]:  # Skip validation for providers that don't require API key
                if not api_key:
                    raise ValueError(
                        f"{llm_provider}: api_key is not set, please set it in the config.toml file."
                    )
                if not model_name:
                    raise ValueError(
                        f"{llm_provider}: model_name is not set, please set it in the config.toml file."
                    )
                if not base_url and llm_provider not in ["gemini"]:
                    raise ValueError(
                        f"{llm_provider}: base_url is not set, please set it in the config.toml file."
                    )

            if llm_provider == "qwen":
                import dashscope
                from dashscope.api_entities.dashscope_response import GenerationResponse

                dashscope.api_key = api_key
                response = dashscope.Generation.call(
                    model=model_name, messages=[{"role": "user", "content": prompt}]
                )
                if response:
                    if isinstance(response, GenerationResponse):
                        status_code = response.status_code
                        if status_code != 200:
                            raise Exception(
                                f'[{llm_provider}] returned an error response: "{response}"'
                            )

                        content = response["output"]["text"]
                        return content.replace("\n", "")
                    else:
                        raise Exception(
                            f'[{llm_provider}] returned an invalid response: "{response}"'
                        )
                else:
                    raise Exception(f"[{llm_provider}] returned an empty response")

            if llm_provider == "gemini":
                import google.generativeai as genai
                from app.services import db
                from app.services.email_service import send_pipeline_email

                keys_to_try = []
                key1 = db.get_setting("gemini_api_key", user_id=user_id) or config.app.get("gemini_api_key")
                if key1:
                    keys_to_try.append(key1)
                for k_idx in range(2, 6):
                    k_val = db.get_setting(f"gemini_api_key_{k_idx}", user_id=user_id) or config.app.get(f"gemini_api_key_{k_idx}")
                    if k_val:
                        keys_to_try.append(k_val)

                if not keys_to_try:
                    raise ValueError("Google Gemini API keys are not configured. Please add one in settings.")

                generation_config = {
                    "temperature": 0.5,
                    "top_p": 1,
                    "top_k": 1,
                    "max_output_tokens": 2048,
                }

                safety_settings = [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_ONLY_HIGH",
                    },
                ]

                errors = []
                success_text = None
                for idx, current_key in enumerate(keys_to_try):
                    logger.info(f"Attempting Gemini generation (Key {idx+1}/{len(keys_to_try)})")
                    try:
                        if not base_url:
                            genai.configure(api_key=current_key, transport="rest")
                        else:
                            genai.configure(api_key=current_key, transport="rest", client_options={'api_endpoint': base_url})

                        model = genai.GenerativeModel(
                            model_name=model_name,
                            generation_config=generation_config,
                            safety_settings=safety_settings,
                        )

                        response = model.generate_content(prompt)
                        candidates = response.candidates
                        generated_text = candidates[0].content.parts[0].text
                        success_text = _normalize_text_response(generated_text, llm_provider)
                        break
                    except Exception as e:
                        logger.error(f"Gemini API key {idx+1} failed during generation: {e}")
                        errors.append(f"Key {idx+1}: {str(e)}")

                if success_text is not None:
                    return success_text

                # If all configured keys failed
                combined_errors = " | ".join(errors)
                logger.error("All configured Gemini API keys failed!")
                try:
                    send_pipeline_email(
                        task_id="gemini-llm-failure-alert",
                        state=-1,
                        progress=0,
                        subject="Gemini API Key Fallback Failure Alert",
                        status_msg="All configured Gemini API keys failed during script generation.",
                        error_msg=f"Encountered errors on all fallback keys:\n{combined_errors}",
                        user_id=user_id
                    )
                except Exception as mail_err:
                    logger.error(f"Failed to send Gemini fallback failure email: {mail_err}")

                raise ValueError(f"All configured Gemini API keys failed: {combined_errors}")

            if llm_provider == "cloudflare":
                response = requests.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a friendly assistant",
                            },
                            {"role": "user", "content": prompt},
                        ]
                    },
                )
                result = response.json()
                logger.info(result)
                return _normalize_text_response(result["result"]["response"], llm_provider)

            if llm_provider == "ernie":
                response = requests.post(
                    "https://aip.baidubce.com/oauth/2.0/token", 
                    params={
                        "grant_type": "client_credentials",
                        "client_id": api_key,
                        "client_secret": secret_key,
                    }
                )
                access_token = response.json().get("access_token")
                url = f"{base_url}?access_token={access_token}"

                payload = json.dumps(
                    {
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.5,
                        "top_p": 0.8,
                        "penalty_score": 1,
                        "disable_search": False,
                        "enable_citation": False,
                        "response_format": "text",
                    }
                )
                headers = {"Content-Type": "application/json"}

                response = requests.request(
                    "POST", url, headers=headers, data=payload
                ).json()
                return _normalize_text_response(response.get("result"), llm_provider)

            if llm_provider == "litellm":
                import litellm

                if not model_name:
                    raise ValueError(
                        f"{llm_provider}: model_name is not set, please set it in the config.toml file."
                    )

                response = litellm.completion(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    drop_params=True,
                )

                if not response:
                    raise ValueError(f"[{llm_provider}] returned empty response")
                if not getattr(response, "choices", None):
                    raise ValueError(f"[{llm_provider}] returned empty response")

                return _extract_chat_completion_text(response, llm_provider)

            if llm_provider == "azure":
                # Azure OpenAI SDK 使用 `azure_endpoint` 和 `api_version` 生成专用请求地址，
                # 不能继续复用下面普通 OpenAI-compatible 的 `base_url` 初始化逻辑。
                # 这里在 Azure 分支内完成请求并立即返回，避免客户端被后续 fallback
                # 覆盖，导致用户配置的 Azure 凭证通过校验但实际请求没有被使用。
                logger.info(f"requesting azure chat completion, model: {model_name}")
                client = AzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=base_url,
                )
                response = client.chat.completions.create(
                    model=model_name, messages=[{"role": "user", "content": prompt}]
                )
                if response:
                    if isinstance(response, ChatCompletion):
                        return _extract_chat_completion_text(response, llm_provider)
                    else:
                        raise Exception(
                            f'[{llm_provider}] returned an invalid response: "{response}", please check your network '
                            f"connection and try again."
                        )
                else:
                    raise Exception(
                        f"[{llm_provider}] returned an empty response, please check your network connection and try again."
                    )

            if llm_provider == "modelscope":
                content = ''
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                )
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    extra_body={"enable_thinking": False},
                    stream=True
                )
                if response:
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            content += delta.content
                    
                    if not content.strip():
                        raise ValueError("Empty content in stream response")
                    
                    return _normalize_text_response(content, llm_provider)
                else:
                    raise Exception(f"[{llm_provider}] returned an empty response")

            else:
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                )

            response = client.chat.completions.create(
                model=model_name, messages=[{"role": "user", "content": prompt}]
            )
            if response:
                if isinstance(response, ChatCompletion):
                    return _extract_chat_completion_text(response, llm_provider)
                else:
                    raise Exception(
                        f'[{llm_provider}] returned an invalid response: "{response}", please check your network '
                        f"connection and try again."
                    )
            else:
                raise Exception(
                    f"[{llm_provider}] returned an empty response, please check your network connection and try again."
                )

        return _normalize_text_response(content, llm_provider)
    except Exception as e:
        return f"Error: {str(e)}"


def _limit_script_text(text: str | None, max_length: int, field_name: str) -> str:
    value = (text or "").strip()
    if len(value) <= max_length:
        return value

    # API 层已经用 Pydantic 做长度校验；这里继续兜底，是为了保护
    # WebUI 或内部服务直接调用 generate_script 时不会把超长提示词发送给模型，
    # 避免 token 成本异常和请求失败。
    logger.warning(
        f"{field_name} is too long and will be truncated to {max_length} characters."
    )
    return value[:max_length]


def _normalize_script_paragraph_number(paragraph_number: int | None) -> int:
    try:
        value = int(paragraph_number or MIN_SCRIPT_PARAGRAPH_NUMBER)
    except (TypeError, ValueError):
        value = MIN_SCRIPT_PARAGRAPH_NUMBER

    if value < MIN_SCRIPT_PARAGRAPH_NUMBER or value > MAX_SCRIPT_PARAGRAPH_NUMBER:
        # WebUI 和 API 都会限制范围；这里兜底处理内部调用，避免异常参数直接扩大
        # LLM 生成成本或生成空结果。
        logger.warning(
            "script paragraph_number is out of range and will be clamped: "
            f"{value}"
        )
        return max(MIN_SCRIPT_PARAGRAPH_NUMBER, min(value, MAX_SCRIPT_PARAGRAPH_NUMBER))

    return value


def build_script_prompt(
    video_subject: str,
    language: str = "",
    paragraph_number: int = 1,
    video_script_prompt: str = "",
    custom_system_prompt: str = "",
    video_duration: int = 30,
    prompt_mode: str = "viral_shorts",
    target_platform: str = "youtube_shorts",
    emotional_tone: str = "inspiring",
    trend_context: str = "",
) -> str:
    paragraph_number = _normalize_script_paragraph_number(paragraph_number)
    video_script_prompt = _limit_script_text(
        video_script_prompt, MAX_SCRIPT_PROMPT_LENGTH, "video_script_prompt"
    )
    custom_system_prompt = _limit_script_text(
        custom_system_prompt, MAX_SCRIPT_SYSTEM_PROMPT_LENGTH, "custom_system_prompt"
    )

    # Calculate word count constraint based on duration (avg 140 WPM = 2.3 words/sec)
    duration_constraint = ""
    if video_duration and video_duration > 0:
        word_count = int(video_duration * 2.3)
        duration_constraint = f"\n- target duration: {video_duration} seconds\n- target script length: approximately {word_count} words"

    # Select prompt template
    template = VIRAL_PROMPT_TEMPLATES.get(prompt_mode, VIRAL_PROMPT_TEMPLATES["viral_shorts"])
    trend_info = f"- Trend context / current event: {trend_context}" if trend_context else ""
    base_prompt = custom_system_prompt or template.format(
        target_platform=target_platform,
        emotional_tone=emotional_tone,
        trend_info=trend_info
    )

    prompt = base_prompt + f"""

# Initialization:
- video subject: {video_subject}
- number of paragraphs: {paragraph_number}{duration_constraint}
""".rstrip()
    if language:
        prompt += f"\n- language: {language}"
    if video_script_prompt:
        prompt += f"""

# Additional User Requirements:
{video_script_prompt}
""".rstrip()

    return prompt


def generate_script(
    video_subject: str,
    language: str = "",
    paragraph_number: int = 1,
    video_script_prompt: str = "",
    custom_system_prompt: str = "",
    video_duration: int = 30,
    user_id: str = "global",
    prompt_mode: str = "viral_shorts",
    target_platform: str = "youtube_shorts",
    emotional_tone: str = "inspiring",
    trend_context: str = "",
) -> str:
    # Dynamically adjust paragraph count based on target duration
    if video_duration and video_duration > 0:
        if video_duration <= 15:
            paragraph_number = 1
        elif video_duration <= 30:
            paragraph_number = 2
        elif video_duration <= 60:
            paragraph_number = 3
        elif video_duration <= 90:
            paragraph_number = 4
        elif video_duration <= 120:
            paragraph_number = 5
        else:
            paragraph_number = 6

    paragraph_number = _normalize_script_paragraph_number(paragraph_number)
    video_script_prompt = _limit_script_text(
        video_script_prompt, MAX_SCRIPT_PROMPT_LENGTH, "video_script_prompt"
    )
    custom_system_prompt = _limit_script_text(
        custom_system_prompt, MAX_SCRIPT_SYSTEM_PROMPT_LENGTH, "custom_system_prompt"
    )
    prompt = build_script_prompt(
        video_subject=video_subject,
        language=language,
        paragraph_number=paragraph_number,
        video_script_prompt=video_script_prompt,
        custom_system_prompt=custom_system_prompt,
        video_duration=video_duration,
        prompt_mode=prompt_mode,
        target_platform=target_platform,
        emotional_tone=emotional_tone,
        trend_context=trend_context,
    )
    final_script = ""
    logger.info(
        f"generating video script for user {user_id}: "
        f"subject={video_subject}, paragraph_number={paragraph_number}, video_duration={video_duration}, "
        f"has_custom_prompt={bool(video_script_prompt.strip())}, "
        f"has_custom_system_prompt={bool(custom_system_prompt.strip())}"
    )

    def format_response(response):
        # Clean the script
        # Remove asterisks, hashes
        response = response.replace("*", "")
        response = response.replace("#", "")

        # Remove markdown syntax
        response = re.sub(r"\[.*\]", "", response)
        response = re.sub(r"\(.*\)", "", response)

        # Split the script into paragraphs
        paragraphs = response.split("\n\n")

        # Select the specified number of paragraphs
        # selected_paragraphs = paragraphs[:paragraph_number]

        # Join the selected paragraphs into a single string
        return "\n\n".join(paragraphs)

    for i in range(_max_retries):
        try:
            response = _generate_response(prompt=prompt, user_id=user_id)
            if response:
                final_script = format_response(response)
            else:
                logging.error("gpt returned an empty response")

            # g4f may return an error message
            if final_script and "当日额度已消耗完" in final_script:
                raise ValueError(final_script)

            if final_script:
                break
        except Exception as e:
            logger.error(f"failed to generate script: {e}")

        if i < _max_retries:
            logger.warning(f"failed to generate video script, trying again... {i + 1}")
    if "Error: " in final_script:
        logger.error(f"failed to generate video script: {final_script}")
    else:
        logger.success(f"completed: \n{final_script}")
    return final_script.strip()


def generate_terms(video_subject: str, video_script: str, amount: int = 5, user_id: str = "global") -> List[str]:
    prompt = f"""
# Role: Video Search Terms Generator

## Goals:
Generate {amount} search terms for stock videos, depending on the subject of a video.

## Constrains:
1. the search terms are to be returned as a json-array of strings.
2. each search term should consist of 1-3 words, always add the main subject of the video.
3. you must only return the json-array of strings. you must not return anything else. you must not return the script.
4. the search terms must be related to the subject of the video.
5. reply with english search terms only.

## Output Example:
["search term 1", "search term 2", "search term 3","search term 4","search term 5"]

## Context:
### Video Subject
{video_subject}

### Video Script
{video_script}

Please note that you must use English for generating video search terms; Chinese is not accepted.
""".strip()

    logger.info(f"subject: {video_subject} for user {user_id}")

    search_terms = []
    response = ""
    for i in range(_max_retries):
        try:
            response = _generate_response(prompt, user_id=user_id)
            if "Error: " in response:
                logger.error(f"failed to generate video script: {response}")
                return response
            search_terms = json.loads(response)
            if not isinstance(search_terms, list) or not all(
                isinstance(term, str) for term in search_terms
            ):
                logger.error("response is not a list of strings.")
                continue

        except Exception as e:
            logger.warning(f"failed to generate video terms: {str(e)}")
            if response:
                match = re.search(r"\[.*]", response)
                if match:
                    try:
                        search_terms = json.loads(match.group())
                    except Exception as e:
                        # 这里保留重试流程，但必须记录 LLM 返回的非标准 JSON，
                        # 否则后续排查搜索词为空时无法定位
                        # 是模型格式问题还是解析逻辑问题。
                        logger.warning(f"failed to generate video terms: {str(e)}")

        if search_terms and len(search_terms) > 0:
            break
        if i < _max_retries:
            logger.warning(f"failed to generate video terms, trying again... {i + 1}")

    logger.success(f"completed: \n{search_terms}")
    return search_terms

def score_script_virality(script: str, user_id: str = "global") -> dict:
    prompt = f"""
# Role: Video Script Virality Predictor
## Objective:
Analyze the provided video script and predict its virality scores across 5 key dimensions.
## Dimensions:
1. hook_score (1-10): How engaging are the first 3 seconds?
2. emotion_score (1-10): Does it tap into a core human emotion (shock, curiosity, urgency, empathy, awe)?
3. clarity_score (1-10): Is the message simple and easy to understand?
4. pacing_score (1-10): Is the structure and syntax optimized for fast, rhythmic delivery?
5. cta_score (1-10): Is there a strong call to action or a loopable ending?

## Overall Score Calculation:
Provide an overall_score (percentage out of 100) calculated based on the dimensions, showing general virality potential.

## Improvement Tip:
Provide a highly specific, actionable sentence of improvement advice.

## Output Format:
Return ONLY a raw JSON object with the keys:
"hook_score", "emotion_score", "clarity_score", "pacing_score", "cta_score", "overall_score", "improvement_tip"

## Script to Analyze:
{script}
""".strip()

    try:
        response = _generate_response(prompt=prompt, user_id=user_id)
        if "Error: " in response:
            raise ValueError(response)
        
        # Clean response
        clean_response = response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_response = "\n".join(lines).strip()
            
        # Parse the JSON
        data = json.loads(clean_response)
        
        # Validate structure and default keys if missing
        scores = {
            "hook_score": int(data.get("hook_score", 5)),
            "emotion_score": int(data.get("emotion_score", 5)),
            "clarity_score": int(data.get("clarity_score", 5)),
            "pacing_score": int(data.get("pacing_score", 5)),
            "cta_score": int(data.get("cta_score", 5)),
            "overall_score": int(data.get("overall_score", 50)),
            "improvement_tip": str(data.get("improvement_tip", "Make the hook punchier."))
        }
        return scores
    except Exception as e:
        logger.error(f"Failed to score script: {e}")
        return {
            "hook_score": 5,
            "emotion_score": 5,
            "clarity_score": 5,
            "pacing_score": 5,
            "cta_score": 5,
            "overall_score": 50,
            "improvement_tip": "Make the hook punchier and enhance the pacing."
        }


def inject_emojis_into_script(script: str, user_id: str = "global") -> str:
    prompt = f"""
Add 1-2 relevant emojis at natural pause points in this script. Return the script with emojis inserted.
Only return the final script with emojis. Do not add any introduction, explanation, or wrap the script in markdown code blocks.

Script:
{script}
""".strip()
    logger.info(f"injecting emojis into script for user {user_id}")
    for i in range(_max_retries):
        try:
            response = _generate_response(prompt=prompt, user_id=user_id)
            if response and not response.startswith("Error:"):
                # Clean up any potential markdown code blocks if the model returned them
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    cleaned = "\n".join(lines).strip()
                return cleaned
        except Exception as e:
            logger.warning(f"failed to inject emojis: {str(e)}")
    return script


if __name__ == "__main__":
    video_subject = "生命的意义是什么"
    script = generate_script(
        video_subject=video_subject, language="zh-CN", paragraph_number=1
    )
    print("######################")
    print(script)
    search_terms = generate_terms(
        video_subject=video_subject, video_script=script, amount=5
    )
    print("######################")
    print(search_terms)
    
