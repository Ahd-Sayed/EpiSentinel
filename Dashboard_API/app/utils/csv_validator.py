class CSVValidationError(Exception):
    def __init__(self, missing_columns):
        self.missing_columns = missing_columns
        super().__init__(f"Missing required columns: {missing_columns}")

def validate_csv_columns(df_columns):
    required_cols = ["VISIT_DATE", "CITY", "COUNTRY", "DISEASE"]
    missing = [col for col in required_cols if col not in df_columns]
    if missing:
        raise CSVValidationError(missing)
