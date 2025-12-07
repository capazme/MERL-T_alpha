#!/usr/bin/env python3
"""
Generate Ground Truth for Codice Penale Libro Primo from Normattiva.

Uses TreeExtractor to get the complete hierarchical structure and article list.
Outputs JSON and Markdown for documentation.
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt.external_sources.visualex.tools.treextractor import (
    get_hierarchical_tree,
    get_all_articles_with_positions,
    NormTree,
    NormNode,
    NormLevel
)

# Codice Penale URN (R.D. 19 ottobre 1930, n. 1398)
CP_URL = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1930-10-19;1398"


def filter_libro_primo(tree: NormTree) -> tuple:
    """
    Filter articles belonging to Libro Primo (Art. 1-240) of the actual Codice Penale.

    The R.D. 1930/1398 contains:
    1. Articles of the promulgation decree (Art. 1-3 without "Libro" in position)
    2. Articles of the Codice Penale proper (with "Libro I" in position)

    Returns:
        tuple: (libro_primo_articles, decreto_promulgazione_articles)
    """
    all_articles = get_all_articles_with_positions(tree)

    libro_primo_articles = []
    decreto_articles = []

    for art in all_articles:
        position = art.get('position', '') or ''

        # Articles with "Libro I" are from the actual Codice Penale
        if 'Libro I' in position:
            # Extract base number
            num_str = art['number'].replace('-', '').replace(' ', '')
            base_num = ''.join(c for c in num_str if c.isdigit())

            try:
                num = int(base_num) if base_num else 0
                # Libro Primo: Art. 1-240 (approximately)
                if 1 <= num <= 240:
                    libro_primo_articles.append(art)
            except ValueError:
                pass
        elif not position or position == '-':
            # Articles without position are from the promulgation decree
            decreto_articles.append(art)

    return libro_primo_articles, decreto_articles


def analyze_structure(tree: NormTree) -> dict:
    """
    Analyze the hierarchical structure of Libro Primo.
    """
    structure = {
        "libri": [],
        "titoli": {},
        "capi": {},
        "sezioni": {}
    }

    def traverse(nodes, current_libro=None, current_titolo=None, current_capo=None):
        for node in nodes:
            if node.level == NormLevel.LIBRO:
                # Check if this is Libro Primo
                if node.number in ["I", "PRIMO", "1"]:
                    structure["libri"].append({
                        "number": node.number,
                        "title": node.title,
                        "n_children": len(node.children)
                    })
                    traverse(node.children, current_libro=node.number)
            elif node.level == NormLevel.TITOLO and current_libro:
                key = f"Titolo {node.number}"
                if key not in structure["titoli"]:
                    structure["titoli"][key] = {
                        "title": node.title,
                        "n_articles": 0
                    }
                traverse(node.children, current_libro, node.number)
            elif node.level == NormLevel.CAPO:
                if current_titolo:
                    key = f"Titolo {current_titolo} - Capo {node.number}"
                    if key not in structure["capi"]:
                        structure["capi"][key] = {
                            "title": node.title,
                            "n_articles": 0
                        }
                traverse(node.children, current_libro, current_titolo, node.number)
            elif node.level == NormLevel.ARTICOLO:
                # Count articles per titolo
                if current_titolo:
                    titolo_key = f"Titolo {current_titolo}"
                    if titolo_key in structure["titoli"]:
                        structure["titoli"][titolo_key]["n_articles"] += 1
                    # Count per capo
                    if current_capo:
                        capo_key = f"Titolo {current_titolo} - Capo {current_capo}"
                        if capo_key in structure["capi"]:
                            structure["capi"][capo_key]["n_articles"] += 1
            else:
                traverse(node.children, current_libro, current_titolo, current_capo)

    traverse(tree.children)
    return structure


async def main():
    print("=" * 60)
    print("GROUND TRUTH GENERATOR - CODICE PENALE LIBRO PRIMO")
    print("=" * 60)
    print(f"Source: Normattiva ({CP_URL})")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Fetch the hierarchical tree
    print("Fetching hierarchical tree from Normattiva...")
    tree, total_count = await get_hierarchical_tree(CP_URL)

    if isinstance(tree, str):
        print(f"ERROR: {tree}")
        return

    print(f"Total articles in R.D. 1398/1930: {total_count}")

    # Filter Libro Primo (separating decree articles from CP articles)
    libro_primo_articles, decreto_articles = filter_libro_primo(tree)
    print(f"Articles in promulgation decree: {len(decreto_articles)}")
    print(f"Articles in Libro Primo CP (1-240): {len(libro_primo_articles)}")

    # Analyze structure
    print("\nAnalyzing structure...")
    structure = analyze_structure(tree)

    # Identify bis/ter/quater articles
    bis_ter_articles = [a for a in libro_primo_articles if any(
        suffix in a['number'].lower()
        for suffix in ['bis', 'ter', 'quater', 'quinquies', 'sexies', 'septies', 'octies']
    )]
    print(f"Articles with bis/ter/etc: {len(bis_ter_articles)}")

    # Build ground truth data
    ground_truth = {
        "metadata": {
            "source": "Normattiva",
            "url": CP_URL,
            "atto": "Regio Decreto 19 ottobre 1930, n. 1398",
            "nome": "Codice Penale",
            "libro": "Primo - Dei reati in generale",
            "timestamp": datetime.now().isoformat(),
            "note": "Il R.D. contiene: (1) articoli del decreto di promulgazione, (2) articoli del Codice Penale"
        },
        "statistics": {
            "total_articles_rd": total_count,
            "articles_decreto_promulgazione": len(decreto_articles),
            "articles_libro_primo_cp": len(libro_primo_articles),
            "articles_bis_ter": len(bis_ter_articles),
        },
        "structure": structure,
        "articles": libro_primo_articles,
        "decreto_promulgazione": decreto_articles,
        "bis_ter_articles": [a['number'] for a in bis_ter_articles],
    }

    # Output paths
    output_dir = Path(__file__).parent.parent / "docs/experiments/EXP-006_libro_primo_cp"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = output_dir / "ground_truth.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)
    print(f"\nSaved JSON to: {json_path}")

    # Generate Markdown
    md_content = generate_markdown(ground_truth)
    md_path = output_dir / "GROUND_TRUTH.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Saved Markdown to: {md_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total R.D. articles: {total_count}")
    print(f"Decreto promulgazione: {len(decreto_articles)}")
    print(f"Libro Primo CP articles: {len(libro_primo_articles)}")
    print(f"Bis/ter articles: {len(bis_ter_articles)}")
    print(f"\nTitoli found: {len(structure['titoli'])}")
    for titolo, info in structure['titoli'].items():
        title_text = info['title'][:50] if info['title'] else 'N/A'
        print(f"  - {titolo}: {title_text}... ({info['n_articles']} art.)")

    return ground_truth


def generate_markdown(gt: dict) -> str:
    """Generate Markdown documentation from ground truth data."""
    md = f"""# Ground Truth: Codice Penale - Libro Primo

> **Source**: Normattiva (fonte ufficiale)
> **URL**: {gt['metadata']['url']}
> **Generated**: {gt['metadata']['timestamp']}

## Atto Normativo

- **Tipo**: {gt['metadata']['atto']}
- **Nome**: {gt['metadata']['nome']}
- **Libro**: {gt['metadata']['libro']}

## Statistiche

| Metrica | Valore |
|---------|--------|
| Articoli totali R.D. 1398/1930 | {gt['statistics']['total_articles_rd']} |
| Articoli decreto promulgazione | {gt['statistics']['articles_decreto_promulgazione']} |
| Articoli Libro Primo CP | {gt['statistics']['articles_libro_primo_cp']} |
| Articoli bis/ter/etc | {gt['statistics']['articles_bis_ter']} |

> **Nota**: Il R.D. 1398/1930 contiene sia gli articoli del decreto di promulgazione (3 articoli)
> che gli articoli del Codice Penale vero e proprio. Per l'ingestion useremo solo gli articoli
> del Codice Penale (quelli con posizione "Libro I").

## Struttura Gerarchica

### Titoli

"""
    # Add titoli
    for titolo, info in gt['structure']['titoli'].items():
        md += f"- **{titolo}**: {info['title']} ({info['n_articles']} articoli)\n"

    md += "\n### Capi\n\n"
    for capo, info in gt['structure']['capi'].items():
        if info['n_articles'] > 0:
            md += f"- {capo}: {info['title']} ({info['n_articles']} articoli)\n"

    md += f"""
## Articoli Bis/Ter/Quater

Articoli con suffisso (introdotti dopo il 1930):

"""
    for art in gt['bis_ter_articles']:
        md += f"- Art. {art}\n"

    md += """
## Elenco Completo Articoli

| # | Articolo | Posizione |
|---|----------|-----------|
"""
    for i, art in enumerate(gt['articles'][:50], 1):  # First 50 for readability
        pos = art.get('position', '-')[:60] if art.get('position') else '-'
        md += f"| {i} | Art. {art['number']} | {pos}... |\n"

    if len(gt['articles']) > 50:
        md += f"\n*... e altri {len(gt['articles']) - 50} articoli (vedi ground_truth.json per elenco completo)*\n"

    md += """
## Note Metodologiche

1. I dati sono estratti direttamente da Normattiva usando il TreeExtractor
2. Il filtro "Libro Primo" include articoli con numero base 1-240
3. Gli articoli bis/ter sono identificati dal suffisso nel numero
4. L'URN di riferimento è: `urn:nir:stato:regio.decreto:1930-10-19;1398`

## Validazione

Questo ground truth sarà usato per validare:
- Conteggio articoli ingestiti
- Struttura gerarchica nel grafo
- Identificazione articoli bis/ter
- Correttezza URN generati
"""
    return md


if __name__ == "__main__":
    asyncio.run(main())
