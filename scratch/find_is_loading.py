with open(r"c:\Users\raman\OneDrive\Desktop\interesting-projects\youtube-automation\MoneyPrinterTurbo\web-platform\src\App.jsx", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "isLoading" in line or "setIsLoading" in line:
        print(f"Line {idx+1}: {line.strip()}")
