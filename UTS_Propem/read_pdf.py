import fitz

doc = fitz.open('uts propem.pdf')
text = ""
for page in doc:
    text += page.get_text()

print(text)
