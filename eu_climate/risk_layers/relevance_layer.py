import pandas as pd
import os

current_dir = os.getcwd()
gdp_path = os.path.join(current_dir, "../data", "L3-estat_gdp.csv", "estat_nama_10r_3gdp_en.csv")


def read_csv_file(file_path):
    """
    Reads a CSV file and returns a DataFrame.
    
    Parameters:
    file_path (str): The path to the CSV file.
    
    Returns:
    pd.DataFrame: The DataFrame containing the CSV data.
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        print(f"Error reading the CSV file: {e}")
        return None

def prepare_gpd(csv_path):
    df = read_csv_file(csv_path)

    df = df[df["TIME_PERIOD"] == 2023]

    nan_counts = df.isna().sum()
    nan_counts = nan_counts[nan_counts ==len(df)]
    df = df.drop(columns=nan_counts.index)

    df = df[df["geo"].str.contains(r"NL(?:[0-9]{3}|[0-9]{2}[A-Z])$")].reset_index(drop=True)
    df = df [df["unit"].str.contains("MIO_EUR")].reset_index(drop=True)
    df = df[["geo", "OBS_VALUE", "unit", "Geopolitical entity (reporting)"]].copy()
    return df

loading_path = os.path.join(current_dir,"data", "L3-estat_road_go_loading", "estat_road_go_na_rl3g_en.csv")
unloading_path = os.path.join(current_dir, "data","L3-estat_road_go_unloading", "estat_road_go_na_ru3g_en.csv")


def load_and_transform_road_freight_transport(csv_path):
    """
    Load and transform road freight transport data.
    
    Returns: 
    pd.DataFrame: Transformed DataFrame with aggregated road freight transport data.
    """
    df = read_csv_file(csv_path)
    if df is None:
        return None

    df = df[df["TIME_PERIOD"] == 2023]

    nan_counts = df.isna().sum()
    nan_counts = nan_counts[nan_counts ==len(df)]
    df = df.drop(columns=nan_counts.index)


    df = df[df["geo"].str.startswith("NL")]

    unqiue_geos = df["geo"].unique()
    print(len(unqiue_geos))
    print(unqiue_geos)
    return df.groupby("geo").agg({
    "OBS_VALUE": "sum",
    "unit": "first",
    "Geopolitical entity (reporting)": "first"
    }).reset_index()


def main():
    gdp_df = prepare_gpd(gdp_path)
    if gdp_df is not None:
        print("GDP DataFrame:")
        print(gdp_df.head())

    loading_df = load_and_transform_road_freight_transport(loading_path)
    if loading_df is not None:
        print("Road Freight Transport Loading DataFrame:")
        print(loading_df.head())

    unloading_df = load_and_transform_road_freight_transport(unloading_path)
    if unloading_df is not None:
        print("Road Freight Transport Unloading DataFrame:")
        print(unloading_df.head())

if __name__ == "__main__":
    main()