from etoe import AtomSelectionCatalog

catalog = AtomSelectionCatalog("data/atom/element")

# Химическая категория
alkali_metals = catalog.categories["alkali-metals"]
print(alkali_metals.symbols)

# Гиператомы пятого атомного уровня
level_five = catalog.levels[5]
print(len(level_five.hyperatoms))

# Конкретная группа гиператомов
x40 = catalog.hyperatom_groups["X-40"]
print(x40.symbols)

# Граф записывается в папку группы X-40
x40.write_graph(catalog.registry, "X-40.dot")