"""Unit tests for product decomposition + supply feasibility map."""

from app.b2b.decompose import build_supply_map, decompose


def test_handloom_decomposes_to_textile_bom():
    cats = {b.category for b in decompose("a natural-dye handloom saree brand")}
    assert {"yarn", "dye"} <= cats


def test_iot_decomposes_to_hardware_bom():
    cats = {b.category for b in decompose("a soil-monitoring IoT device for farms")}
    assert {"pcb", "sensor"} <= cats


def test_unknown_product_is_reported_honestly():
    # an unrecognised product says so, instead of inventing a packaging line (F-A4-011)
    cats = {b.category for b in decompose("something entirely novel xyz")}
    assert cats == {"unknown_product"}


def test_cue_does_not_misfire_inside_a_word():
    # "iot" inside "patriot" and "smart" inside a saree must not pull in a PCB (F-A4-011)
    assert "pcb" not in {b.category for b in decompose("patriot flags and banners")}
    assert "pcb" not in {b.category for b in decompose("smart-looking handloom sarees")}


def test_knitwear_and_leather_resolve():
    # F-B4-007: these resolve to the textile/leather bill, not unknown
    assert "yarn" in {b.category for b in decompose("a knitwear brand")}
    assert "unknown_product" not in {b.category for b in decompose("handmade leather bags")}


async def test_supply_map_matches_covered_lines():
    smap = await build_supply_map("handloom saree", monthly_units=1000, district="Tiruppur")
    by_cat = {sl.line.category: sl for sl in smap}
    # yarn, dye, packaging, printing all have seed suppliers → no gaps
    assert by_cat["yarn"].matches and not by_cat["yarn"].gap
    assert by_cat["yarn"].matches[0].supply.id == "y1"  # Tiruppur ranks top on geo


async def test_supply_map_flags_gaps():
    # a BOM line whose category has no seed supplier → gap
    from app.b2b.decompose import BOMLine

    smap = await build_supply_map("custom", bom=[BOMLine("unobtainium", "rare", 1, "unit")])
    assert smap[0].gap and smap[0].matches == []
