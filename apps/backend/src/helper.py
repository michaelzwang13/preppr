import joblib
import numpy as np
import pandas as pd

# load model
try:
    model = joblib.load("src/resources/nyuhack25_600.pkl")
except Exception as e:
    print("Error loading model: ", e)
    model = None


# predict impulsive purchase
def predict_impulsive_purchase(carbs=0, sugar=0, sodium=0, fat=0):
    sample = {}
    sample["Data.Carbohydrate"] = carbs
    sample["Data.Sugar Total"] = sugar
    sample["Data.Major Minerals.Sodium"] = sodium
    sample["Data.Fat.Saturated Fat"] = fat
    print(carbs, sugar, sodium, fat)
    sample_df = pd.DataFrame([sample])
    return model.predict(sample_df)


def model_learn(carbs, sugar, sodium, fat):
    sample = {}
    sample["Data.Carbohydrate"] = carbs
    sample["Data.Sugar Total"] = sugar
    sample["Data.Major Minerals.Sodium"] = sodium
    sample["Data.Fat.Saturated Fat"] = fat
    sample["Label"] = 0
    sample_df = pd.DataFrame([sample])

    x = sample_df[
        [
            "Data.Carbohydrate",
            "Data.Sugar Total",
            "Data.Major Minerals.Sodium",
            "Data.Fat.Saturated Fat",
        ]
    ]
    y = sample_df["Label"]

    model.partial_fit(x, y)

    return model
