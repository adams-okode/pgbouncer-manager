# CLI

## Installation

```bash
pip install -r requirements.txt
```

## Commands

### tenant-add

```bash
python -m cli.tenant tenant-add \
  --id=tenant1 \
  --host=db.example.com \
  --password=secret123
```

### tenant-list

```bash
python -m cli.tenant tenant-list
```

### tenant-update

```bash
python -m cli.tenant tenant-update \
  --id=tenant1 \
  --pool-size=20
```

### tenant-remove

```bash
python -m cli.tenant tenant-remove --id=tenant1
```

### pools-list

```bash
python -m cli.tenant pools-list
```

### reload

```bash
python -m cli.tenant reload
```
