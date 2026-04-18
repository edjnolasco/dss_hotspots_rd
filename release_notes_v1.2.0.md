# DSS_Hotspots_RD v1.2.0

## 🚀 Overview

Version 1.2.0 introduces a major enhancement to the DSS by incorporating a multi-model predictive framework, enabling comparative evaluation of machine learning algorithms within the decision-making pipeline.

This version transitions the system from a single-model approach to a flexible, extensible architecture aligned with modern data science practices.

---

## ✨ Key Features

### Multi-Model Engine
- Random Forest
- Extra Trees
- Gradient Boosting
- HistGradientBoosting
- SVM (SVR with RBF kernel)

### Benchmarking System
- Automatic comparison of models
- Metrics:
  - MAE
  - RMSE
  - R²
- Temporal validation strategy

### Exportable Artifacts
- Benchmark tables (CSV, XLSX)
- Benchmark figures (PNG)
- Ready for academic reporting (Word / APA)

### UI Enhancements
- Model selector (sidebar)
- Benchmark toggle
- Integrated visualization

---

## 🧠 Technical Highlights

- Decoupled predictive layer from DSS rules engine
- Support for non-linear models (SVM)
- Fallback interpretability strategy:
  - SHAP
  - Feature importance
  - Permutation importance
- Modular architecture for future extensibility

---

## 📊 Impact

This version significantly improves:

- Reproducibility
- Model transparency
- Decision support robustness
- Academic validity of the system

---

## 🧪 Intended Use

- Academic research (ML + DSS)
- Decision support prototyping
- Transport safety analytics

---

## 👤 Author

Edwin José Nolasco

---

## 📌 Notes

This release represents a methodological upgrade and should be considered a stable base for further experimentation and scaling.
