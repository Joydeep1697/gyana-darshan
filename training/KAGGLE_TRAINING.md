# Nyaya Darshana: recoverable Kaggle model training

The original notebook trained a 235 MB LoRA adapter and then exhausted GPU
memory while loading a second 8B model for a checkpoint sweep. The notebook
failed, and its final adapter was not present in the saved Kaggle outputs.

## What the repaired pipeline changes

- Audits non-empty train, validation, and optional test datasets before using a GPU.
- Blocks malformed records, known fabricated statute names, and split leakage.
- Uses one visible GPU and one 4-bit base model throughout training and evaluation.
- Saves rolling checkpoints and automatically resumes from the newest checkpoint.
- Uses evaluation-based early stopping and restores the best validation checkpoint.
- Saves `adapter_model.safetensors`, adapter configuration, and tokenizer before
  running any legal evaluation.
- Writes a downloadable `/kaggle/working/nyaya_model_release.zip` immediately
  after saving the adapter and refreshes it with the final evaluation report.
- Checks actual statutory meaning, rejects invented laws, and blocks deployment
  unless every critical legal probe passes and total accuracy reaches 90%.
- Never repeats the previous checkpoint sweep or loads a second base model.

## Kaggle execution

1. Download `training/nyaya_kaggle_recovery.ipynb` from this repository.
2. Open Kaggle and import that notebook, or replace the code in the existing
   `NYAYA MODEL` notebook.
3. Attach the original private dataset containing `train.jsonl` and
   `validation.jsonl`. Attach `test.jsonl` when available.
4. Enable a GPU accelerator. Enable internet access if dependencies or the base
   model must be downloaded.
5. Add `HF_TOKEN` as a Kaggle secret if the selected base model requires it.
6. Run all cells and save the notebook version.
7. Download `nyaya_model_release.zip` from the Output tab.
8. Inspect `reports/legal_evaluation.json`. Connect the adapter to production
   only when `release_ready` is `true`.

The expected release contents are:

```text
nyaya_model_release/
  adapter/
    adapter_model.safetensors
    adapter_config.json
    tokenizer files
  reports/
    dataset_audit.json
    training_report.json
    legal_evaluation.json
```

Optional environment variables include `NYAYA_BASE_MODEL`, `NYAYA_MAX_STEPS`,
`NYAYA_MAX_LENGTH`, `NYAYA_MINIMUM_ACCURACY`, `NYAYA_TRAIN_FILE`,
`NYAYA_VALIDATION_FILE`, and `NYAYA_TEST_FILE`.

For a fast infrastructure smoke test, set `NYAYA_MAX_STEPS=10`. A smoke-test
adapter is not deployment-ready unless it independently passes the legal gate.
