from google.cloud import bigquery
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import GroupKFold, cross_val_predict


PROJECT_ID = "california-hospital-pricing"

QUERY = """
SELECT
    msdrg_code,
    payer_family,
    payer_category,
    ucla_price,
    sutter_price,
    ucla_vs_sutter_ratio,
    log_price_ratio
FROM
    `california-hospital-pricing.hospital_pricing.mart_ucla_sutter_paired_differences`
WHERE
    log_price_ratio IS NOT NULL
"""


def load_data():
    client = bigquery.Client(project=PROJECT_ID)
    df = client.query(QUERY).to_dataframe()

    print(f"Rows loaded: {len(df):,}")
    print(f"Unique MS-DRGs: {df['msdrg_code'].nunique():,}")
    print()
    print(df["payer_category"].value_counts())
    print()
    print(df["payer_family"].value_counts())

    return df


def run_linear_model(df):
    features = [
        "payer_family",
        "payer_category",
    ]

    X = df[features]
    y = df["log_price_ratio"]

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    drop="first",
                    sparse_output=False,
                ),
                features,
            )
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            ("model", Ridge(alpha=1.0)),
        ]
    )

    # Keep the same DRG entirely within one fold.
    groups = df["msdrg_code"]

    cv = GroupKFold(n_splits=5)

    predictions = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        groups=groups,
    )

    r2 = r2_score(y, predictions)
    mae = mean_absolute_error(y, predictions)

    print("\nRidge regression")
    print("-----------------")
    print(f"Grouped CV R²:  {r2:.4f}")
    print(f"Grouped CV MAE: {mae:.4f}")

    model.fit(X, y)

    feature_names = (
        model.named_steps["preprocessing"]
        .get_feature_names_out()
    )

    coefficients = model.named_steps["model"].coef_

    coef_df = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
        }
    )

    coef_df["multiplicative_effect"] = np.exp(
        coef_df["coefficient"]
    )

    coef_df["pct_effect"] = (
        coef_df["multiplicative_effect"] - 1
    ) * 100

    print("\nCoefficients")
    print("------------")
    print(
        coef_df
        .sort_values("coefficient")
        .to_string(index=False)
    )

    return model


def run_random_forest(df):
    features = [
        "payer_family",
        "payer_category",
    ]

    X = df[features]
    y = df["log_price_ratio"]

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
                features,
            )
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=300,
                    max_depth=6,
                    min_samples_leaf=10,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    groups = df["msdrg_code"]
    cv = GroupKFold(n_splits=5)

    predictions = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        groups=groups,
    )

    r2 = r2_score(y, predictions)
    mae = mean_absolute_error(y, predictions)

    print("\nRandom Forest")
    print("-------------")
    print(f"Grouped CV R²:  {r2:.4f}")
    print(f"Grouped CV MAE: {mae:.4f}")

    model.fit(X, y)

    feature_names = (
        model.named_steps["preprocessing"]
        .get_feature_names_out()
    )

    importances = model.named_steps[
        "model"
    ].feature_importances_

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": importances,
        }
    )

    print("\nFeature importance")
    print("------------------")
    print(
        importance_df
        .sort_values(
            "importance",
            ascending=False,
        )
        .to_string(index=False)
    )

    return model

def evaluate_by_payer_category(df):
    print("\nPerformance by payer category")
    print("=============================")

    for category in ["Commercial", "Medicare"]:
        subset = df[df["payer_category"] == category].copy()

        X = subset[["payer_family"]]
        y = subset["log_price_ratio"]
        groups = subset["msdrg_code"]

        n_splits = min(5, groups.nunique())
        cv = GroupKFold(n_splits=n_splits)

        # Ridge
        ridge_preprocessing = ColumnTransformer(
            transformers=[
                (
                    "categorical",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        drop="first",
                        sparse_output=False,
                    ),
                    ["payer_family"],
                )
            ]
        )

        ridge = Pipeline(
            steps=[
                ("preprocessing", ridge_preprocessing),
                ("model", Ridge(alpha=1.0)),
            ]
        )

        ridge_predictions = cross_val_predict(
            ridge,
            X,
            y,
            cv=cv,
            groups=groups,
        )

        ridge_r2 = r2_score(
            y,
            ridge_predictions,
        )

        ridge_mae = mean_absolute_error(
            y,
            ridge_predictions,
        )

        # Random Forest
        rf_preprocessing = ColumnTransformer(
            transformers=[
                (
                    "categorical",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                    ["payer_family"],
                )
            ]
        )

        rf = Pipeline(
            steps=[
                ("preprocessing", rf_preprocessing),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=300,
                        max_depth=6,
                        min_samples_leaf=10,
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        )

        rf_predictions = cross_val_predict(
            rf,
            X,
            y,
            cv=cv,
            groups=groups,
        )

        rf_r2 = r2_score(
            y,
            rf_predictions,
        )

        rf_mae = mean_absolute_error(
            y,
            rf_predictions,
        )

        print(f"\n{category}")
        print("-" * len(category))
        print(f"Rows: {len(subset):,}")
        print(
            f"Unique MS-DRGs: "
            f"{subset['msdrg_code'].nunique():,}"
        )

        print("\nRidge")
        print(f"Grouped CV R²:  {ridge_r2:.4f}")
        print(f"Grouped CV MAE: {ridge_mae:.4f}")

        print("\nRandom Forest")
        print(f"Grouped CV R²:  {rf_r2:.4f}")
        print(f"Grouped CV MAE: {rf_mae:.4f}")

def main():
    df = load_data()

    run_linear_model(df)
    run_random_forest(df)
    evaluate_by_payer_category(df)


if __name__ == "__main__":
    main()