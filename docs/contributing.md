# Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

## Development

```bash
# Install dependencies
pip install -r requirements.txt
cd ui && npm install

# Run tests
pytest
cd ui && npm test

# Run linter
ruff check .
cd ui && npm run lint
```
