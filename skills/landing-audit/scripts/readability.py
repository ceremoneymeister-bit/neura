#!/usr/bin/env python3
"""Russian text readability analysis (Flesch-Ru, Fog-Ru)."""
import argparse, json, re, sys

RUSSIAN_VOWELS = set('аеёиоуыэюяАЕЁИОУЫЭЮЯ')

def count_syllables_ru(word):
    """Count syllables in a Russian word by counting vowels."""
    return sum(1 for c in word if c in RUSSIAN_VOWELS) or 1

def analyze(text):
    # Split into sentences (by . ! ? … and newlines followed by uppercase)
    sentences = re.split(r'[.!?…]+|\n+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Split into words
    words = re.findall(r'[а-яёА-ЯЁa-zA-Z]+', text)

    if not words or not sentences:
        return {'error': 'Not enough text to analyze'}

    word_count = len(words)
    sentence_count = len(sentences)
    total_syllables = sum(count_syllables_ru(w) for w in words)
    complex_words = sum(1 for w in words if count_syllables_ru(w) >= 4)

    asl = word_count / sentence_count  # Average Sentence Length
    asw = total_syllables / word_count  # Average Syllables per Word

    # Flesch Reading Ease adapted for Russian
    flesch_ru = round(206.835 - 1.3 * asl - 60.1 * asw, 1)

    # Gunning Fog Index for Russian
    complex_pct = (complex_words / word_count) * 100
    fog_ru = round(0.4 * (asl + complex_pct), 1)

    return {
        'flesch_ru': flesch_ru,
        'fog_ru': fog_ru,
        'word_count': word_count,
        'sentence_count': sentence_count,
        'avg_sentence_len': round(asl, 1),
        'avg_syllables_per_word': round(asw, 2),
        'complex_words_pct': round(complex_pct, 1),
        'assessment': (
            'Очень лёгкий' if flesch_ru >= 80 else
            'Лёгкий' if flesch_ru >= 60 else
            'Средний' if flesch_ru >= 40 else
            'Сложный' if flesch_ru >= 20 else
            'Очень сложный'
        )
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', help='Path to text file')
    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    result = analyze(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
