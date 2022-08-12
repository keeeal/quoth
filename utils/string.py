from re import findall


def find_urls(text: str) -> list[str]:
    pattern = "".join(
        [
            r"(https?:\/\/(?:www\.|(?!www))",
            r"[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]",
            r"\.[^\s]{2,}|www\.",
            r"[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]",
            r"\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))",
            r"[a-zA-Z0-9]+\.[^\s]{2,}|",
            r"www\.[a-zA-Z0-9]+\.[^\s]{2,})",
        ]
    )
    return findall(pattern, text)


def truncate(text: str, length: int = 128):
    line = text.replace("\n", " ")
    return (line[: length - 3] + "...") if len(line) > length else line
