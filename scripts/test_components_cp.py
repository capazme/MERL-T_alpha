#!/usr/bin/env python3
"""
Test components for Codice Penale ingestion.

Verifies:
1. TreeExtractor - get article list
2. NormattivaScraper - fetch article text
3. BrocardiScraper - fetch enrichment
4. MultivigenzaPipeline - get modification history
"""
import asyncio
import sys
sys.path.insert(0, '.')

from merlt.external_sources.visualex.tools.norma import Norma, NormaVisitata
from merlt.external_sources.visualex.scrapers.normattiva_scraper import NormattivaScraper
from merlt.external_sources.visualex.scrapers.brocardi_scraper import BrocardiScraper
from merlt.external_sources.visualex.tools.treextractor import get_hierarchical_tree, get_all_articles_with_positions


# Codice Penale: R.D. 19 ottobre 1930, n. 1398
CP_URL = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1930-10-19;1398"


async def test_treextractor():
    """Test TreeExtractor per ottenere lista articoli."""
    print("\n" + "=" * 60)
    print("TEST 1: TreeExtractor")
    print("=" * 60)

    tree, count = await get_hierarchical_tree(CP_URL)

    if isinstance(tree, str):
        print(f"❌ ERRORE: {tree}")
        return False

    print(f"✅ Articoli totali estratti: {count}")

    # Get all articles with positions
    articles = get_all_articles_with_positions(tree)
    libro_primo = [a for a in articles if a.get('position') and 'Libro I' in a.get('position', '')]

    print(f"✅ Articoli Libro Primo: {len(libro_primo)}")

    # Show first 5
    print("\nPrimi 5 articoli Libro I:")
    for art in libro_primo[:5]:
        print(f"  - Art. {art['number']}: {art.get('position', '-')[:50]}...")

    return True


async def test_normattiva_scraper():
    """Test NormattivaScraper per fetchare testo articolo."""
    print("\n" + "=" * 60)
    print("TEST 2: NormattivaScraper")
    print("=" * 60)

    scraper = NormattivaScraper()

    # Test Art. 43 (elemento soggettivo del reato - dolo/colpa)
    norma = Norma(tipo_atto='regio decreto', data='1930-10-19', numero_atto='1398')
    nv = NormaVisitata(norma=norma, numero_articolo='43')

    print(f"Fetching Art. 43 CP...")
    print(f"URN: {nv.urn}")

    try:
        testo, urn = await scraper.get_document(nv)
        print(f"✅ Testo recuperato: {len(testo)} caratteri")
        print(f"\nPrimi 300 caratteri:")
        print(testo[:300] + "...")
        return True
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        return False


async def test_brocardi_scraper():
    """Test BrocardiScraper per enrichment."""
    print("\n" + "=" * 60)
    print("TEST 3: BrocardiScraper")
    print("=" * 60)

    scraper = BrocardiScraper()

    # Test Art. 52 (legittima difesa)
    norma = Norma(tipo_atto='codice penale', data=None, numero_atto=None)
    nv = NormaVisitata(norma=norma, numero_articolo='52')

    print(f"Checking Brocardi for Art. 52 CP (legittima difesa)...")

    try:
        result = await scraper.do_know(nv)
        if result:
            txt, link = result
            print(f"✅ Found on Brocardi: {link}")

            # Try to get full content with get_info
            testo, info, url = await scraper.get_info(nv)
            if testo:
                print(f"✅ Testo articolo: {len(testo)} caratteri")
            if info:
                print(f"✅ Info keys: {list(info.keys())}")
                if 'massime' in info:
                    print(f"   - Massime: {len(info.get('massime', []))} trovate")
                if 'spiegazione' in info:
                    print(f"   - Spiegazione: {len(info.get('spiegazione', ''))} caratteri")
            return True
        else:
            print("⚠️ Articolo non trovato su Brocardi")
            return False
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_amendment_history():
    """Test fetching amendment history for an article."""
    print("\n" + "=" * 60)
    print("TEST 4: Amendment History (Multivigenza)")
    print("=" * 60)

    scraper = NormattivaScraper()

    # Test Art. 52 (legittima difesa - molto modificato)
    norma = Norma(tipo_atto='regio decreto', data='1930-10-19', numero_atto='1398')
    nv = NormaVisitata(norma=norma, numero_articolo='52')

    print(f"Fetching amendment history for Art. 52 CP...")

    try:
        modifiche = await scraper.get_amendment_history(nv, filter_article=True)
        print(f"✅ Trovate {len(modifiche)} modifiche")

        if modifiche:
            print("\nUltime 3 modifiche:")
            for m in modifiche[-3:]:
                print(f"  - {m.data_efficacia}: {m.tipo_modifica.value}")
                print(f"    Atto: {m.atto_modificante_estremi[:60]}...")

        return True
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 60)
    print("COMPONENT TESTS FOR CODICE PENALE INGESTION")
    print("=" * 60)

    results = {}

    # Run tests
    results['treextractor'] = await test_treextractor()
    results['normattiva'] = await test_normattiva_scraper()
    results['brocardi'] = await test_brocardi_scraper()
    results['amendments'] = await test_amendment_history()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ All components working! Ready for ingestion.")
    else:
        print("\n⚠️ Some components failed. Fix before proceeding.")

    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
