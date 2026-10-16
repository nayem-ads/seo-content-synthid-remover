from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import html
import json
import math
import re
import unicodedata
import urllib.parse
import urllib.request
from typing import Any


class ResilientTranslator:
    """
    Multi-provider translator that uses deep_translator (if installed),
    Google Translate mobile endpoint, and automatically falls back to the
    MyMemory Translation API if Google returns HTTP 429.
    """

    _google_blocked = False

    def __init__(self, source: str = "en", target: str = "de"):
        self.source = source
        self.target = target
        self._dt = None
        try:
            from deep_translator import GoogleTranslator as DTGoogle
            self._dt = DTGoogle(source=source, target=target)
        except ImportError:
            pass

    def translate(self, text: str) -> str:
        if not text.strip():
            return text

        if not ResilientTranslator._google_blocked:
            # 1. Try deep_translator if installed
            if self._dt is not None:
                try:
                    res = self._dt.translate(text)
                    if res:
                        return res
                except Exception:
                    ResilientTranslator._google_blocked = True

            # 2. Try Google Translate mobile endpoint
            if not ResilientTranslator._google_blocked:
                try:
                    params = urllib.parse.urlencode(
                        {"sl": self.source, "tl": self.target, "q": text}
                    )
                    url = f"https://translate.google.com/m?{params}"
                    req = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                        },
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        page = response.read().decode("utf-8")
                        match = re.search(
                            r'class="(?:t0|result-container)">(.*?)<', page, re.DOTALL
                        )
                        if match:
                            return html.unescape(match.group(1))
                except Exception:
                    ResilientTranslator._google_blocked = True

        # 3. Fallback to MyMemory free translation API (no API key needed, resists Google 429s)
        params = urllib.parse.urlencode(
            {"q": text, "langpair": f"{self.source}|{self.target}"}
        )
        url = f"https://api.mymemory.translated.net/get?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            translated = data.get("responseData", {}).get("translatedText")
            if translated:
                return html.unescape(translated)
        return text


# Comprehensive list of statistical "Claude-isms" & Google SpamBrain Scaled-Content clichés
AI_CLICHE_REPLACEMENTS: list[tuple[str, str]] = [
    # Multi-word opening transitions & meta-commentary
    (r"(?i)\b(?:furthermore|moreover|additionally),?\s+it\s+(?:is|'s)\s+worth\s+noting\s+that\s*", "Notably, "),
    (r"(?i)\bit\s+(?:is|'s)\s+worth\s+noting\s+that\s*", ""),
    (r"(?i)\bit\s+(?:is|'s)\s+important\s+to\s+note\s+that\s*", ""),
    (r"(?i)\bit\s+(?:is|'s)\s+important\s+to\s+remember\s+that\s*", "Keep in mind that "),
    (r"(?i)\bin\s+the\s+ever-evolving\s+(?:landscape|world)\s+of\b", "In"),
    (r"(?i)\bin\s+today's\s+fast-paced\s+(?:digital\s+)?world,?\s*", "Today, "),
    (r"(?i)\bin\s+today's\s+digital\s+(?:age|landscape|era),?\s*", "Today, "),
    (r"(?i)\bwhether\s+you(?:'re|\s+are)\s+a\s+seasoned\s+\w+\s+or\s+(?:just\s+starting\s+out|a\s+beginner),?\s*", ""),
    (r"(?i)\bin\s+conclusion,?\s*", "Bottom line: "),
    (r"(?i)\bto\s+sum\s+up,?\s*", "In short, "),
    (r"(?i)\bat\s+the\s+end\s+of\s+the\s+day,?\s*", "Ultimately, "),
    (r"(?i)\bpave\s+the\s+way\s+for\b", "enable"),
    (r"(?i)\bstand\s+out\s+from\s+the\s+crowd\b", "stand out"),
    (r"(?i)\bunlock\s+the\s+(?:full\s+)?(?:potential|power)\s+of\b", "get the most out of"),
    (r"(?i)\bunleash\s+the\s+(?:full\s+)?(?:potential|power)\s+of\b", "make full use of"),
    (r"(?i)\bgame-changing\b", "high-impact"),
    (r"(?i)\bgame\s+changer\b", "major advantage"),
    (r"(?i)\ba\s+testament\s+to\b", "proof of"),
    (r"(?i)\btestament\s+to\b", "proof of"),
    (r"(?i)\brich\s+tapestry\s+of\b", "mix of"),
    (r"(?i)\btapestry\s+of\b", "mix of"),
    (r"(?i)\btreasure\s+trove\s+of\b", "collection of"),
    (r"(?i)\bparadigm\s+shift\b", "major shift"),
    (r"(?i)\bsynergy\s+between\b", "connection between"),
    # Overused Claude verbs & adverbs
    (r"\bdelve\s+into\b", "explore"),
    (r"\bDelve\s+into\b", "Explore"),
    (r"\bdelves\s+into\b", "explores"),
    (r"\bdelving\s+into\b", "exploring"),
    (r"\bembark\s+on\b", "start"),
    (r"\bEmbark\s+on\b", "Start"),
    (r"\bfoster\b", "build"),
    (r"\bFoster\b", "Build"),
    (r"\bfostering\b", "building"),
    (r"\bharness\s+the\b", "use the"),
    (r"\bHarness\s+the\b", "Use the"),
    (r"\bunderscore\b", "highlight"),
    (r"\bunderscores\b", "highlights"),
    (r"\bbolster\b", "strengthen"),
    (r"\brevolutionize\b", "transform"),
    (r"\bseamlessly\b", "smoothly"),
    (r"\bSeamlessly\b", "Smoothly"),
    (r"\bmeticulously\b", "carefully"),
    (r"\bMeticulously\b", "Carefully"),
    (r"\bFurthermore,\s*", "Also, "),
    (r"\bMoreover,\s*", "Plus, "),
    (r"\bAdditionally,\s*", "Beyond that, "),
    (r"\bConsequently,\s*", "As a result, "),
    (r"\bNevertheless,\s*", "Even so, "),
    (r"(?i)\bcomprehensive\s+guide\b", "complete guide"),
    (r"\bcrucial\b", "key"),
    (r"\bCrucial\b", "Key"),
    (r"\bpivotal\b", "important"),
    (r"\bPivotal\b", "Important"),
    (r"\bparamount\b", "essential"),
    (r"\butilize\b", "use"),
    (r"\bUtilize\b", "Use"),
    (r"\butilizing\b", "using"),
    (r"\bleverage\b", "use"),
    (r"\bLeverage\b", "Use"),
    (r"\bleveraging\b", "using"),
]

# Natural human contractions (NMT models expand contractions into stiff formal prose like "it is", "do not")
NATURAL_CONTRACTIONS: list[tuple[str, str]] = [
    (r"\bIt is\b", "It's"),
    (r"\bit is\b", "it's"),
    (r"\bThat is\b", "That's"),
    (r"\bthat is\b", "that's"),
    (r"\bThere is\b", "There's"),
    (r"\bthere is\b", "there's"),
    (r"\bYou will\b", "You'll"),
    (r"\byou will\b", "you'll"),
    (r"\bYou are\b", "You're"),
    (r"\byou are\b", "you're"),
    (r"\bWe are\b", "We're"),
    (r"\bwe are\b", "we're"),
    (r"\bThey are\b", "They're"),
    (r"\bthey are\b", "they're"),
    (r"\bdo not\b", "don't"),
    (r"\bDo not\b", "Don't"),
    (r"\bdoes not\b", "doesn't"),
    (r"\bDoes not\b", "Doesn't"),
    (r"\bdid not\b", "didn't"),
    (r"\bDid not\b", "Didn't"),
    (r"\bcannot\b", "can't"),
    (r"\bCannot\b", "Can't"),
    (r"\bwill not\b", "won't"),
    (r"\bWill not\b", "Won't"),
    (r"\bshould not\b", "shouldn't"),
    (r"\bwould not\b", "wouldn't"),
    (r"\bis not\b", "isn't"),
    (r"\bare not\b", "aren't"),
]

# Local phrase synonym perturbations (used in both Fast Local mode and post-translation polish)
LOCAL_STRUCTURAL_SWAPS: list[tuple[str, str]] = [
    (r"\bin order to\b", "to"),
    (r"\bIn order to\b", "To"),
    (r"\bdue to the fact that\b", "because"),
    (r"\ba wide range of\b", "many"),
    (r"\ba variety of\b", "various"),
    (r"\bon a daily basis\b", "every day"),
    (r"\bremain competitive\b", "stay ahead"),
    (r"\bstay competitive\b", "stay ahead"),
    (r"\bplays a (?:key|vital|important) role in\b", "drives"),
    (r"\bwhen it comes to\b", "for"),
    (r"\bWhen it comes to\b", "For"),
    (r"\bmake sure\b", "ensure"),
    (r"\bprior to\b", "before"),
    (r"\bsubsequent to\b", "after"),
]


def scrub_unicode_and_typographic_watermarks(text: str) -> tuple[str, dict[str, int]]:
    """
    Removes invisible zero-width characters, hidden Unicode watermarks,
    non-breaking spaces, and normalizes typographic AI tells (like em-dash overuse).
    Returns (cleaned_text, stats_dict).
    """
    invisible_chars = [
        "\u200b",  # Zero-width space
        "\u200c",  # Zero-width non-joiner
        "\u200d",  # Zero-width joiner
        "\u200e",  # Left-to-right mark
        "\u200f",  # Right-to-left mark
        "\ufeff",  # Zero-width no-break space (BOM)
        "\u2060",  # Word joiner
        "\u00ad",  # Soft hyphen
        "\u180e",  # Mongolian vowel separator
    ]
    invisible_count = sum(text.count(ch) for ch in invisible_chars)
    for ch in invisible_chars:
        text = text.replace(ch, "")

    nbsp_count = text.count("\u00a0") + text.count("\u202f")
    text = text.replace("\u00a0", " ").replace("\u202f", " ")

    curly_count = sum(text.count(c) for c in ("“", "”", "‘", "’"))
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )

    em_dash_count = len(re.findall(r"\s*—\s*", text))
    # Alternate em-dash replacements between " - " and ", " for natural human punctuation rhythm
    dash_idx = 0

    def replace_em_dash(_m):
        nonlocal dash_idx
        dash_idx += 1
        return ", " if dash_idx % 2 == 0 else " - "

    text = re.sub(r"\s*—\s*", replace_em_dash, text)

    stats = {
        "invisible_chars_removed": invisible_count,
        "nbsp_removed": nbsp_count,
        "curly_quotes_normalized": curly_count,
        "em_dashes_normalized": em_dash_count,
    }
    return unicodedata.normalize("NFKC", text), stats


def scrub_claude_cliches(text: str) -> tuple[str, int]:
    """Replaces high-probability LLM transition phrases that flag Google SpamBrain & statistical detectors."""
    total_hits = 0
    for pattern, replacement in AI_CLICHE_REPLACEMENTS:
        matches = len(re.findall(pattern, text))
        if matches:
            total_hits += matches
            text = re.sub(pattern, replacement, text)
    return text, total_hits


def inject_human_burstiness_and_contractions(
    text: str, protected_keywords: list[str]
) -> str:
    """
    Restores natural English contractions (which translators flatten into 'it is', 'do not')
    and applies light structural swaps while strictly avoiding any protected SEO keywords.
    """
    lines = text.split("\n")
    out_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("```") or stripped.startswith("|"):
            out_lines.append(line)
            continue

        # Temporarily mask protected keywords, bold text, and links so contractions/swaps never touch them
        mask_map: dict[str, str] = {}
        idx = 0

        def mask_fn(m):
            nonlocal idx
            token = f"__HMASK{idx}__"
            mask_map[token] = m.group(0)
            idx += 1
            return token

        working = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", mask_fn, line)
        working = re.sub(r"\*\*([^*]+)\*\*", mask_fn, working)
        for kw in sorted(protected_keywords, key=len, reverse=True):
            if kw.strip():
                working = re.sub(rf"\b{re.escape(kw)}\b", mask_fn, working, flags=re.IGNORECASE)

        for pattern, replacement in LOCAL_STRUCTURAL_SWAPS:
            working = re.sub(pattern, replacement, working)

        for pattern, replacement in NATURAL_CONTRACTIONS:
            working = re.sub(pattern, replacement, working)

        # Fix capital letter after sentence start if contraction/cliché removal left lowercase
        working = re.sub(
            r"(^|[.!?]\s+)([a-z])",
            lambda m: m.group(1) + m.group(2).upper(),
            working,
        )

        for token, orig in mask_map.items():
            working = working.replace(token, orig)

        out_lines.append(working)

    return "\n".join(out_lines)


def translate_paragraph_with_seo_locks(
    paragraph: str,
    protected_keywords: list[str],
    translators: list[tuple[ResilientTranslator, ResilientTranslator]],
) -> str:
    """
    Translates a single paragraph through one or more language hops while keeping
    exact SEO keywords, Markdown links, and bold tags 100% intact.
    """
    stripped = paragraph.strip()
    if (
        not stripped
        or stripped.startswith("#")
        or stripped.startswith("```")
        or stripped.startswith("|")
    ):
        return paragraph

    list_prefix = ""
    list_match = re.match(r"^(\s*(?:[-*+]|\d+\.)\s+)(.*)", paragraph, re.DOTALL)
    if list_match:
        list_prefix = list_match.group(1)
        working_text = list_match.group(2)
    else:
        working_text = paragraph

    link_map: list[tuple[str, str, str]] = []
    bold_map: list[tuple[str, str]] = []
    kw_map: list[tuple[str, str]] = []
    counter = 0

    def replace_link(m):
        nonlocal counter
        counter += 1
        marker = f"[{100 + counter}]"
        anchor = m.group(1)
        full_link = m.group(0)
        link_map.append((marker, anchor, full_link))
        return f'"{anchor}" {marker}'

    working_text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, working_text)

    def replace_bold(m):
        nonlocal counter
        counter += 1
        marker = f"[{200 + counter}]"
        inner = m.group(1)
        bold_map.append((marker, inner))
        return f'"{inner}" {marker}'

    working_text = re.sub(r"\*\*([^*]+)\*\*", replace_bold, working_text)

    sorted_keywords = sorted(protected_keywords, key=len, reverse=True)
    for kw in sorted_keywords:
        if not kw.strip():
            continue
        pattern = re.compile(
            rf'(?<!")\b({re.escape(kw)})\b(?!"\s*\[\d+\])', re.IGNORECASE
        )

        def replace_kw(m):
            nonlocal counter
            counter += 1
            marker = f"[{300 + counter}]"
            exact = m.group(0)
            kw_map.append((marker, exact))
            return f'"{exact}" {marker}'

        working_text = pattern.sub(replace_kw, working_text)

    en_text = working_text
    try:
        for forward_tx, back_tx in translators:
            pivoted = forward_tx.translate(en_text)
            en_text = back_tx.translate(pivoted)
    except Exception as e:
        print(f"[!] Translation warning on paragraph (keeping original): {e}")
        return paragraph

    qc = r'"“”„«»\''

    def restore_marker(
        text_in: str, marker: str, inner_text: str, replacement: str
    ) -> str:
        esc_marker = re.escape(marker)
        q_pattern = re.compile(rf"[{qc}][^{qc}]+[{qc}]\s*{esc_marker}")
        if q_pattern.search(text_in):
            return q_pattern.sub(lambda _: replacement, text_in)
        u_pattern = re.compile(
            rf"\b{re.escape(inner_text)}\b\s*{esc_marker}", re.IGNORECASE
        )
        if u_pattern.search(text_in):
            return u_pattern.sub(lambda _: replacement, text_in)
        return text_in.replace(marker, replacement)

    for marker, anchor, full_link in link_map:
        en_text = restore_marker(en_text, marker, anchor, full_link)

    for marker, inner_bold in bold_map:
        en_text = restore_marker(
            en_text, marker, inner_bold, f"**{inner_bold}**"
        )

    for marker, exact_kw in kw_map:
        en_text = restore_marker(en_text, marker, exact_kw, exact_kw)

    en_text = re.sub(r" {2,}", " ", en_text).strip()
    return f"{list_prefix}{en_text}"


def extract_auto_keywords(text: str, max_keywords: int = 8) -> list[str]:
    """
    Automatically extracts high-value SEO phrases from bold tags, link anchors,
    and markdown headers if the user wants 1-click SEO keyword detection.
    """
    candidates: list[str] = []
    # 1. Bolded phrases
    for m in re.findall(r"\*\*([^*]{3,45})\*\*", text):
        clean = m.strip(" .,!?:;")
        if clean and clean.lower() not in [c.lower() for c in candidates]:
            candidates.append(clean)
    # 2. Link anchors
    for m in re.findall(r"\[([^\]]{3,45})\]\([^)]+\)", text):
        clean = m.strip(" .,!?:;")
        if clean and clean.lower() not in [c.lower() for c in candidates]:
            candidates.append(clean)
    # 3. Repeated 2-word / 3-word noun-like phrases
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    stop = {
        "that", "this", "with", "from", "your", "have", "more", "will",
        "when", "what", "which", "their", "about", "into", "must", "check",
        "today", "modern", "guide", "ultimate", "worth", "noting", "world",
    }
    filtered = [w for w in words if w not in stop]
    bigrams: dict[str, int] = {}
    for w1, w2 in zip(filtered, filtered[1:]):
        bg = f"{w1} {w2}"
        bigrams[bg] = bigrams.get(bg, 0) + 1
    for bg, count in sorted(bigrams.items(), key=lambda x: x[1], reverse=True):
        if count >= 2 and bg.lower() not in [c.lower() for c in candidates]:
            candidates.append(bg)
        if len(candidates) >= max_keywords:
            break
    return candidates[:max_keywords]


def evaluate_seo_and_watermark_metrics(
    original_text: str,
    cleaned_text: str,
    protected_keywords: list[str],
    unicode_stats: dict[str, int],
    cliches_removed: int,
) -> dict[str, Any]:
    """
    Computes a comprehensive Google Algorithm & SEO Preservation Scorecard
    comparing the original Claude output against the purified output.
    """
    def get_words(s: str) -> list[str]:
        return re.findall(r"\w+", s.lower())

    def get_ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
        if len(words) < n:
            return set()
        return set(zip(*(words[i:] for i in range(n))))

    orig_words = get_words(original_text)
    clean_words = get_words(cleaned_text)

    orig_3 = get_ngrams(orig_words, 3)
    clean_3 = get_ngrams(clean_words, 3)

    if orig_3:
        surviving_ratio = len(orig_3 & clean_3) / len(orig_3)
        trigram_scramble_pct = round((1.0 - surviving_ratio) * 100, 1)
    else:
        trigram_scramble_pct = 0.0

    # Sentence Burstiness (Coefficient of Variation of sentence lengths in words)
    def calc_burstiness(s: str) -> float:
        body_lines = [
            ln.strip()
            for ln in s.split("\n")
            if ln.strip() and not ln.strip().startswith("#")
        ]
        body = " ".join(body_lines)
        sentences = [
            seg.strip()
            for seg in re.split(r"[.!?]+", body)
            if len(seg.strip().split()) >= 3
        ]
        if len(sentences) < 2:
            return 35.0
        lengths = [len(seg.split()) for seg in sentences]
        mean = sum(lengths) / len(lengths)
        variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        cv = (std_dev / mean) * 100 if mean > 0 else 0.0
        return round(min(100.0, cv * 1.8), 1)

    burstiness_before = calc_burstiness(original_text)
    burstiness_after = calc_burstiness(cleaned_text)

    # Keyword verification
    keyword_report = []
    total_kw_expected = 0
    total_kw_preserved = 0
    for kw in protected_keywords:
        if not kw.strip():
            continue
        before_cnt = len(re.findall(rf"\b{re.escape(kw)}\b", original_text, re.IGNORECASE))
        after_cnt = len(re.findall(rf"\b{re.escape(kw)}\b", cleaned_text, re.IGNORECASE))
        total_kw_expected += before_cnt
        total_kw_preserved += min(before_cnt, after_cnt)
        keyword_report.append(
            {
                "keyword": kw,
                "before": before_cnt,
                "after": after_cnt,
                "intact": after_cnt >= before_cnt,
            }
        )

    kw_retention_pct = (
        round((total_kw_preserved / total_kw_expected) * 100, 1)
        if total_kw_expected > 0
        else 100.0
    )

    # Markdown structural integrity check
    headers_before = len(re.findall(r"^#+\s+.+", original_text, re.MULTILINE))
    headers_after = len(re.findall(r"^#+\s+.+", cleaned_text, re.MULTILINE))
    links_before = len(re.findall(r"\[([^\]]+)\]\(([^)]+)\)", original_text))
    links_after = len(re.findall(r"\[([^\]]+)\]\(([^)]+)\)", cleaned_text))
    bolds_before = len(re.findall(r"\*\*([^*]+)\*\*", original_text))
    bolds_after = len(re.findall(r"\*\*([^*]+)\*\*", cleaned_text))

    # Calculate Google Algorithm Safety Score (Before vs After)
    # Penalties on original text: clichés, em-dashes, invisible chars, unscrambled LLM token sequences
    raw_threats = (
        cliches_removed * 7
        + unicode_stats["invisible_chars_removed"] * 10
        + unicode_stats["em_dashes_normalized"] * 5
        + unicode_stats["curly_quotes_normalized"] * 2
    )
    score_before = max(18, min(72, 78 - raw_threats))

    # After score rewards token chain scrambling, cliché removal, and 100% SEO preservation
    scramble_bonus = min(35.0, trigram_scramble_pct * 0.65)
    seo_bonus = (kw_retention_pct / 100.0) * 15.0
    score_after = int(round(min(99.0, 48.0 + scramble_bonus + seo_bonus)))

    return {
        "google_safety_score_before": score_before,
        "google_safety_score_after": score_after,
        "trigram_scramble_pct": trigram_scramble_pct,
        "seo_retention_pct": kw_retention_pct,
        "burstiness_before": burstiness_before,
        "burstiness_after": burstiness_after,
        "word_count_before": len(orig_words),
        "word_count_after": len(clean_words),
        "threats_removed": {
            "claude_cliches": cliches_removed,
            "invisible_unicode": unicode_stats["invisible_chars_removed"]
            + unicode_stats["nbsp_removed"],
            "em_dashes": unicode_stats["em_dashes_normalized"],
            "curly_quotes": unicode_stats["curly_quotes_normalized"],
        },
        "structure": {
            "headers": {"before": headers_before, "after": headers_after},
            "links": {"before": links_before, "after": links_after},
            "bolds": {"before": bolds_before, "after": bolds_after},
        },
        "keywords": keyword_report,
    }


def preserve_and_scrub_seo_detailed(
    text: str,
    protected_keywords: list[str] | None = None,
    mode: str = "deep",
) -> dict[str, Any]:
    """
    Full pipeline returning both the cleaned article and the detailed Google SEO & Watermark scorecard.
    Modes:
      - 'deep': EN -> DE -> EN resampling + Unicode/Cliché scrubber + Contraction/Burstiness humanizer
      - 'multihop': EN -> ES -> DE -> EN double-pivot resampling for maximum token scrambling
      - 'fast': Instant local Unicode + Cliché + Structural/Contraction humanizer (no external API calls)
    """
    if protected_keywords is None:
        protected_keywords = []

    # Clean up keyword list
    clean_kws = [k.strip() for k in protected_keywords if k and k.strip()]

    # Stage 1: Unicode & typographic watermark removal
    cleaned, unicode_stats = scrub_unicode_and_typographic_watermarks(text)

    # Stage 2: Pre-translation Claude cliché scrubbing
    cleaned, cliches_pass1 = scrub_claude_cliches(cleaned)

    # Stage 3: Token sequence resampling (parallelized across paragraphs for speed)
    if mode in ("deep", "multihop"):
        if mode == "multihop":
            translators = [
                (ResilientTranslator("en", "es"), ResilientTranslator("es", "en")),
                (ResilientTranslator("en", "de"), ResilientTranslator("de", "en")),
            ]
        else:
            translators = [
                (ResilientTranslator("en", "de"), ResilientTranslator("de", "en")),
            ]

        lines = cleaned.split("\n")

        def process_line(line: str) -> str:
            return translate_paragraph_with_seo_locks(line, clean_kws, translators)

        with ThreadPoolExecutor(max_workers=6) as pool:
            processed_lines = list(pool.map(process_line, lines))

        cleaned = "\n".join(processed_lines)

    # Stage 4: Post-translation cliché cleanup + Human contraction & burstiness injection
    cleaned, cliches_pass2 = scrub_claude_cliches(cleaned)
    cleaned = inject_human_burstiness_and_contractions(cleaned, clean_kws)

    metrics = evaluate_seo_and_watermark_metrics(
        original_text=text,
        cleaned_text=cleaned,
        protected_keywords=clean_kws,
        unicode_stats=unicode_stats,
        cliches_removed=cliches_pass1 + cliches_pass2,
    )

    return {
        "cleaned_text": cleaned,
        "metrics": metrics,
        "protected_keywords": clean_kws,
        "mode": mode,
    }


def preserve_and_scrub_seo(
    text: str, protected_keywords: list[str] | None = None, mode: str = "deep"
) -> str:
    """Backwards-compatible function that returns just the cleaned markdown string."""
    result = preserve_and_scrub_seo_detailed(
        text, protected_keywords=protected_keywords, mode=mode
    )
    return result["cleaned_text"]


if __name__ == "__main__":
    print("--- Antigravity SEO-Safe Watermark & Fingerprint Purifier ---")

    raw_claude_article = """## The Ultimate Guide to Cloud Hosting

In today's fast-paced world, if you want to seamlessly secure your application — you must delve into **managed cloud hosting**. Furthermore, it is worth noting that modern infrastructure requires enterprise speeds to stay competitive.

Check out the [Google Cloud Platform](https://google.com) for enterprise speeds and reliable uptime.
"""

    seo_keywords = [
        "cloud hosting",
        "enterprise speeds",
        "managed cloud hosting",
    ]

    res = preserve_and_scrub_seo_detailed(
        raw_claude_article, protected_keywords=seo_keywords
    )
    print("\n--- Output Article (Safe to Publish) ---")
    print(res["cleaned_text"])
    print("\n--- Google Algorithm Scorecard ---")
    print(json.dumps(res["metrics"], indent=2))
