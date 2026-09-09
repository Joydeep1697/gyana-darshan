# Kaggle Training Notes

Kaggle training is optional research work and is not part of the deployed product path.

Use Kaggle only with private inputs for `train.jsonl`, `validation.jsonl`, optional `test.jsonl`, and any existing adapter archive. Generated notebooks, adapters, zipped releases, and reports must stay in private storage or Kaggle outputs; they are ignored by this repository.

Before any adapter is considered for product use:

- run the dataset audits in this directory
- run legal probe evaluation against the current retrieval-grounded baseline
- keep the full output package outside Git
- complete external legal validation before making accuracy or launch claims

No adapter is deployment-ready merely because a training run finishes or a local score passes.
