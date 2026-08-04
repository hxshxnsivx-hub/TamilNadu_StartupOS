"""Unit tests for product decomposition + supply feasibility map."""

from app.b2b.decompose import build_supply_map, decompose


def test_handloom_decomposes_to_textile_bom():
    cats = {b.category for b in decompose("a natural-dye handloom saree brand")}
    assert {"yarn", "dye"} <= cats


def test_iot_decomposes_to_hardware_bom():
    cats = {b.category for b in decompose("a soil-monitoring IoT device for farms")}
    assert {"pcb", "sensor"} <= cats


def test_unknown_product_falls_back_to_packaging():
    cats = {b.category for b in decompose("something entirely novel xyz")}
    assert cats == {"packaging"}


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
