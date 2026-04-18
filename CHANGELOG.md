# Changelog

All notable changes to this project will be documented in this file.

---

## [1.2.0] - 2026-04-17

### ✨ Added
- Multi-model predictive engine (Random Forest, Extra Trees, Gradient Boosting, HistGradientBoosting, SVR-RBF).
- Dynamic model selection from UI (Streamlit).
- Benchmark module for comparative evaluation of models.
- Automatic export of benchmark artifacts:
  - Tables (CSV, XLSX)
  - Figures (PNG)
- Visualization of model performance (MAE, RMSE, R²).
- Integration of SVM (SVR with RBF kernel) into DSS pipeline.
- Structured experimental evaluation aligned with temporal split strategy.

### 🧠 Improved
- DSS architecture refactored to support pluggable predictive models.
- Separation between predictive component and rule-based inference layer.
- Enhanced narrative generation including model metadata.
- Improved interpretability fallback (SHAP → feature importance → permutation importance).
- Export workflow aligned with academic reporting (figures + tables).

### 📊 Data Science
- Implementation of benchmarking framework for model comparison.
- Temporal validation strategy to avoid data leakage.
- Standardization of evaluation metrics:
  - MAE
  - RMSE
  - R²

### 🎯 UI / UX
- New “Motor predictivo” selector in sidebar.
- Optional benchmark execution via checkbox.
- Embedded visualization of model comparison.
- Export controls integrated into UI.

### 🐛 Fixed
- Streamlit deprecation warning (`use_container_width` → `width="stretch"`).
- Session state stability issues in map interaction.
- Minor fixes in pipeline output consistency.

---

## [1.1.0] - 2026-04-08
- Initial DSS version with Random Forest baseline.
- Ranking Top-K and rule-based prioritization.
- Executive narrative generation.
- Export functionality (CSV).
- Interactive map with drill-down.

---

## [1.0.0]
- Initial conceptual version (not formally released).