from google.cloud import bigquery

import numpy as np
import pandas as pd

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


def validate_predictions(predictions, model_name):
    """Fail immediately if a model produces invalid predictions."""

    if not np.isfinite(predictions).all():
        invalid_count = np.sum(~np.isfinite(predictions))

        raise ValueError(
            f"{model_name} produced "
            f"{invalid_count} non-finite predictions."
        )


def load_data():
    client = bigquery.Client(
        project=PROJECT_ID
    )

    df = client.query(
        QUERY
    ).to_dataframe()

    # Explicit numeric conversion for modeling.
    numeric_columns = [
        "ucla_price",
        "sutter_price",
        "ucla_vs_sutter_ratio",
        "log_price_ratio",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "msdrg_code",
            "payer_family",
            "payer_category",
            "log_price_ratio",
        ]
    ).copy()

    print(
        f"Rows loaded: {len(df):,}"
    )

    print(
        f"Unique MS-DRGs: "
        f"{df['msdrg_code'].nunique():,}"
    )

    print(
        "\npayer_category"
    )

    print(
        df["payer_category"]
        .value_counts()
    )

    print(
        "\npayer_family"
    )

    print(
        df["payer_family"]
        .value_counts()
    )

    return df


def run_ridge_model(df):
    """
    Basic additive Ridge model.

    log price ratio
        ~ payer family
        + payer category
    """

    features = [
        "payer_family",
        "payer_category",
    ]

    X = df[features]

    y = (
        df["log_price_ratio"]
        .astype(np.float64)
        .to_numpy()
    )

    groups = df[
        "msdrg_code"
    ]

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    drop="first",
                    sparse_output=False,
                    dtype=np.float64,
                ),
                features,
            )
        ]
    )

    model = Pipeline(
        steps=[
            (
                "preprocessing",
                preprocessing,
            ),
            (
                "model",
                Ridge(
                    alpha=1.0
                ),
            ),
        ]
    )

    cv = GroupKFold(
        n_splits=5
    )

    predictions = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        groups=groups,
    )

    validate_predictions(
        predictions,
        "Basic Ridge",
    )

    r2 = r2_score(
        y,
        predictions,
    )

    mae = mean_absolute_error(
        y,
        predictions,
    )

    print(
        "\nRidge regression"
    )

    print(
        "-----------------"
    )

    print(
        f"Grouped CV R²:  {r2:.4f}"
    )

    print(
        f"Grouped CV MAE: {mae:.4f}"
    )

    model.fit(
        X,
        y,
    )

    feature_names = (
        model
        .named_steps[
            "preprocessing"
        ]
        .get_feature_names_out()
    )

    coefficients = (
        model
        .named_steps[
            "model"
        ]
        .coef_
    )

    coef_df = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
        }
    )

    coef_df[
        "multiplicative_effect"
    ] = np.exp(
        coef_df[
            "coefficient"
        ]
    )

    coef_df[
        "pct_effect"
    ] = (
        coef_df[
            "multiplicative_effect"
        ] - 1
    ) * 100

    print(
        "\nCoefficients"
    )

    print(
        "------------"
    )

    print(
        coef_df
        .sort_values(
            "coefficient"
        )
        .to_string(
            index=False
        )
    )

    return model


def run_interaction_ridge(df):
    """
    Ridge model using insurer × payer-category combinations.

    This allows the effect of an insurer to differ between
    Commercial and Medicare contracts.
    """

    interaction_df = df.copy()

    interaction_df[
        "payer_family_category"
    ] = (
        interaction_df[
            "payer_family"
        ]
        + "__"
        + interaction_df[
            "payer_category"
        ]
    )

    features = [
        "payer_family_category"
    ]

    X = interaction_df[
        features
    ]

    y = (
        interaction_df[
            "log_price_ratio"
        ]
        .astype(np.float64)
        .to_numpy()
    )

    groups = interaction_df[
        "msdrg_code"
    ]

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    drop="first",
                    sparse_output=False,
                    dtype=np.float64,
                ),
                features,
            )
        ]
    )

    model = Pipeline(
        steps=[
            (
                "preprocessing",
                preprocessing,
            ),
            (
                "model",
                Ridge(
                    alpha=1.0
                ),
            ),
        ]
    )

    cv = GroupKFold(
        n_splits=5
    )

    predictions = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        groups=groups,
    )

    validate_predictions(
        predictions,
        "Interaction Ridge",
    )

    r2 = r2_score(
        y,
        predictions,
    )

    mae = mean_absolute_error(
        y,
        predictions,
    )

    print(
        "\nRidge with payer interactions"
    )

    print(
        "-----------------------------"
    )

    print(
        f"Grouped CV R²:  {r2:.4f}"
    )

    print(
        f"Grouped CV MAE: {mae:.4f}"
    )

    model.fit(
        X,
        y,
    )

    feature_names = (
        model
        .named_steps[
            "preprocessing"
        ]
        .get_feature_names_out()
    )

    coefficients = (
        model
        .named_steps[
            "model"
        ]
        .coef_
    )

    coef_df = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
        }
    )

    coef_df[
        "multiplicative_effect"
    ] = np.exp(
        coef_df[
            "coefficient"
        ]
    )

    coef_df[
        "pct_effect"
    ] = (
        coef_df[
            "multiplicative_effect"
        ] - 1
    ) * 100

    print(
        "\nInteraction coefficients"
    )

    print(
        "------------------------"
    )

    print(
        coef_df
        .sort_values(
            "coefficient"
        )
        .to_string(
            index=False
        )
    )

    return model


def run_random_forest(df):
    """
    Nonlinear benchmark model.
    """

    features = [
        "payer_family",
        "payer_category",
    ]

    X = df[
        features
    ]

    y = (
        df[
            "log_price_ratio"
        ]
        .astype(np.float64)
        .to_numpy()
    )

    groups = df[
        "msdrg_code"
    ]

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                    dtype=np.float64,
                ),
                features,
            )
        ]
    )

    model = Pipeline(
        steps=[
            (
                "preprocessing",
                preprocessing,
            ),
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

    cv = GroupKFold(
        n_splits=5
    )

    predictions = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        groups=groups,
    )

    validate_predictions(
        predictions,
        "Random Forest",
    )

    r2 = r2_score(
        y,
        predictions,
    )

    mae = mean_absolute_error(
        y,
        predictions,
    )

    print(
        "\nRandom Forest"
    )

    print(
        "-------------"
    )

    print(
        f"Grouped CV R²:  {r2:.4f}"
    )

    print(
        f"Grouped CV MAE: {mae:.4f}"
    )

    model.fit(
        X,
        y,
    )

    feature_names = (
        model
        .named_steps[
            "preprocessing"
        ]
        .get_feature_names_out()
    )

    importances = (
        model
        .named_steps[
            "model"
        ]
        .feature_importances_
    )

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": importances,
        }
    )

    print(
        "\nFeature importance"
    )

    print(
        "------------------"
    )

    print(
        importance_df
        .sort_values(
            "importance",
            ascending=False,
        )
        .to_string(
            index=False
        )
    )

    return model


def evaluate_by_payer_category(df):
    """
    Evaluate insurer-family predictive performance separately
    for Commercial and Medicare observations.
    """

    print(
        "\nPerformance by payer category"
    )

    print(
        "============================="
    )

    for category in [
        "Commercial",
        "Medicare",
    ]:

        subset = (
            df[
                df[
                    "payer_category"
                ] == category
            ]
            .copy()
        )

        features = [
            "payer_family"
        ]

        X = subset[
            features
        ]

        y = (
            subset[
                "log_price_ratio"
            ]
            .astype(np.float64)
            .to_numpy()
        )

        groups = subset[
            "msdrg_code"
        ]

        n_splits = min(
            5,
            groups.nunique(),
        )

        cv = GroupKFold(
            n_splits=n_splits
        )

        # ----------------------------------------
        # Ridge
        # ----------------------------------------

        ridge_preprocessing = (
            ColumnTransformer(
                transformers=[
                    (
                        "categorical",
                        OneHotEncoder(
                            handle_unknown="ignore",
                            drop="first",
                            sparse_output=False,
                            dtype=np.float64,
                        ),
                        features,
                    )
                ]
            )
        )

        ridge = Pipeline(
            steps=[
                (
                    "preprocessing",
                    ridge_preprocessing,
                ),
                (
                    "model",
                    Ridge(
                        alpha=1.0
                    ),
                ),
            ]
        )

        ridge_predictions = (
            cross_val_predict(
                ridge,
                X,
                y,
                cv=cv,
                groups=groups,
            )
        )

        validate_predictions(
            ridge_predictions,
            f"{category} Ridge",
        )

        ridge_r2 = r2_score(
            y,
            ridge_predictions,
        )

        ridge_mae = (
            mean_absolute_error(
                y,
                ridge_predictions,
            )
        )

        # ----------------------------------------
        # Random Forest
        # ----------------------------------------

        rf_preprocessing = (
            ColumnTransformer(
                transformers=[
                    (
                        "categorical",
                        OneHotEncoder(
                            handle_unknown="ignore",
                            sparse_output=False,
                            dtype=np.float64,
                        ),
                        features,
                    )
                ]
            )
        )

        rf = Pipeline(
            steps=[
                (
                    "preprocessing",
                    rf_preprocessing,
                ),
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

        rf_predictions = (
            cross_val_predict(
                rf,
                X,
                y,
                cv=cv,
                groups=groups,
            )
        )

        validate_predictions(
            rf_predictions,
            f"{category} Random Forest",
        )

        rf_r2 = r2_score(
            y,
            rf_predictions,
        )

        rf_mae = (
            mean_absolute_error(
                y,
                rf_predictions,
            )
        )

        # ----------------------------------------
        # Output
        # ----------------------------------------

        print(
            f"\n{category}"
        )

        print(
            "-" * len(category)
        )

        print(
            f"Rows: "
            f"{len(subset):,}"
        )

        print(
            f"Unique MS-DRGs: "
            f"{subset['msdrg_code'].nunique():,}"
        )

        print(
            "\nRidge"
        )

        print(
            f"Grouped CV R²:  "
            f"{ridge_r2:.4f}"
        )

        print(
            f"Grouped CV MAE: "
            f"{ridge_mae:.4f}"
        )

        print(
            "\nRandom Forest"
        )

        print(
            f"Grouped CV R²:  "
            f"{rf_r2:.4f}"
        )

        print(
            f"Grouped CV MAE: "
            f"{rf_mae:.4f}"
        )


def main():
    df = load_data()

    run_ridge_model(
        df
    )

    run_interaction_ridge(
        df
    )

    run_random_forest(
        df
    )

    evaluate_by_payer_category(
        df
    )


if __name__ == "__main__":
    main()