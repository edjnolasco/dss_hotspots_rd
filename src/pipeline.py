from .features import create_features
from .modeling import prepare_training_data, temporal_train_test_split, train_model, evaluate_model, score_dataframe, FEATURES
from .rules import apply_rules
from .metrics import ranking_metrics
from .explain import explain_global
from .narrative import build_narrative

def run_pipeline(normalized_df, random_state: int = 42):
    feat_df = create_features(normalized_df)
    trainable_df = prepare_training_data(feat_df)
    train_df, test_df, train_years, test_years = temporal_train_test_split(trainable_df)
    fit_df = train_df if not train_df.empty else trainable_df
    model = train_model(fit_df, random_state=random_state)
    mae, r2 = evaluate_model(model, test_df)
    scored_df = apply_rules(score_dataframe(model, feat_df))
    latest_year = int(scored_df["year"].max())
    ranking_df = (
        scored_df[scored_df["year"] == latest_year]
        .groupby("provincia", as_index=False)
        .agg(pred_fallecidos_next=("pred_fallecidos_next", "mean"),
             score_riesgo=("score_riesgo", "mean"),
             categoria=("categoria", "first"),
             fallecidos_actuales=("fallecidos", "sum"))
        .sort_values("score_riesgo", ascending=False)
        .reset_index(drop=True)
    )
    metricas_df, pred_rank_df, actual_rank_df = ranking_metrics(scored_df)
    explain_df = explain_global(model, fit_df[FEATURES])
    narrative_text = build_narrative(ranking_df, metricas_df, latest_year)
    return {
        "feat_df": feat_df, "trainable_df": trainable_df, "scored_df": scored_df,
        "ranking_df": ranking_df, "metricas_df": metricas_df, "pred_rank_df": pred_rank_df,
        "actual_rank_df": actual_rank_df, "explain_df": explain_df, "narrative_text": narrative_text,
        "latest_year": latest_year, "train_years": train_years, "test_years": test_years,
        "mae": mae, "r2": r2
    }
