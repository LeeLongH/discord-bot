def splitMsg(message):
    """
    Check if a number is inside a sentence.
    If exactly one number is found, return it.
    Otherwise, return False.
    """
    words = message.content.split()
    numbers = []

    for word in words:
        number = is_whole_number_int(word)
        
        if number is not None:
            print(f"Number inside msg {number}")

        if number is not None:
            numbers.append(number)
            if len(numbers) > 1:
                return False  # More than one number found → return False immediately

    return numbers[0] if len(numbers) == 1 else 0


def is_whole_number_int(content: str):
    """
    Check if a string is an integer.
    Try whole string, or string without last character.
    """
    for attempt in (content.strip(), content.strip()[:-1]):
        try:
            return int(attempt)
        except ValueError:
            continue
    return None
