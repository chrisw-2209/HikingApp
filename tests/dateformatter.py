def format_date(text):
    formatted_text = ''.join([char for char in text if char.isdigit()])
    if len(formatted_text) < 4:
        return formatted_text
    elif len(formatted_text) == 4:
        return formatted_text+"-"
    elif len(formatted_text) < 6:
        return formatted_text[0:4]+"-"+formatted_text[4:]
    elif len(formatted_text) == 6:
        return formatted_text[0:4]+"-"+formatted_text[4:]+"-"
    else:
        return formatted_text[0:4]+"-"+formatted_text[4:6]+"-"+formatted_text[6:8]
    

tests = [
    "-",
    "20",
    "200",
    "2006",
    "20060",
    "2006-01",
    "2006010",
    "20060101",
    "200601011",
]

for test in tests:
    print(test, "->", format_date(test))