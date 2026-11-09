# backend/study/citation_gen.py — APA / MLA / Chicago / IEEE citations

_STYLES = ("apa", "mla", "chicago", "ieee")


class CitationGen:
    def styles(self):
        return list(_STYLES)

    def format(self, fields: dict, style: str = "apa"):
        fields = fields or {}
        style = (style or "apa").lower()
        if style not in _STYLES:
            raise ValueError(f"unsupported style '{style}' (use {', '.join(_STYLES)})")

        authors = (fields.get("authors") or "").strip()
        title = (fields.get("title") or "").strip()
        year = str(fields.get("year") or "n.d.").strip()
        publisher = (fields.get("publisher") or "").strip()
        journal = (fields.get("journal") or "").strip()
        url = (fields.get("url") or "").strip()
        volume = str(fields.get("volume") or "").strip()
        pages = str(fields.get("pages") or "").strip()
        accessed = str(fields.get("accessed") or "").strip()

        if style == "apa":
            text = f"{authors} ({year}). {title}."
            if journal:
                text += f" {journal}"
                if volume:
                    text += f", {volume}"
                if pages:
                    text += f", {pages}"
                text += "."
            elif publisher:
                text += f" {publisher}."
            if url:
                text += f" {url}"
        elif style == "mla":
            text = f'{authors}. "{title}."'
            if journal:
                text += f" {journal}"
                if volume:
                    text += f", vol. {volume}"
                if pages:
                    text += f", pp. {pages}"
            elif publisher:
                text += f" {publisher},"
            text += f" {year}."
            if url:
                text += f" {url}. Accessed {accessed or 'today'}."
        elif style == "chicago":
            text = f'{authors}. "{title}."'
            if journal:
                text += f" {journal}"
                if volume:
                    text += f" {volume}"
                if pages:
                    text += f": {pages}"
            elif publisher:
                text += f" {publisher}"
            text += f" ({year})."
            if url:
                text += f" {url}."
        else:  # ieee
            text = f'{authors}, "{title},"'
            if journal:
                text += f" {journal}"
                if volume:
                    text += f", vol. {volume}"
                if pages:
                    text += f", pp. {pages}"
            text += f", {year}."
            if url:
                text += f" [Online]. Available: {url}"

        return {"style": style, "citation": " ".join(text.split())}


citations = CitationGen()
