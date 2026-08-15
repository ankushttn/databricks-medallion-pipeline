# Seed Data Notes

## Source Files

| File | Entity | Rows | Status |
|------|--------|------|--------|
| `data/customers.csv` | Customers | 10,010 | Generated |
| `data/orders.csv` | Orders | 100,020 | Generated |
| `data/products.csv` | Products | 500 | Generated |

## Generation

```bash
python src/data_generation/generate_sample_data.py --output-dir data --seed 42
```

See `src/data_generation/DATA_GENERATION_NOTES.md` for schema, defects, and validation details.

## Column Definitions

See `data-model.md` §2 for full field specifications.
