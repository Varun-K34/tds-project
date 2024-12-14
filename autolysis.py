import os
import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import openai
import numpy as np
from dotenv import load_dotenv

# Function to retrieve the API token from environment variables
# or a command-line argument.
def get_api_token():
    """Retrieve API token from environment variable or command-line argument."""
    token = os.getenv("AIPROXY_TOKEN")
    if token:
        print("API token retrieved from environment variables.")
    else:
        print("API token not found in environment variables.")
    return token


if load_dotenv():
    print(".env file loaded successfully.")
else:
    print("Failed to load .env file.")

print("Loaded AIPROXY_TOKEN:", os.getenv("AIPROXY_TOKEN"))


# Function to create an output directory for saving plots and generated README.
def create_output_directory(file_path):
    """Create an output directory based on the input file name."""
    base_name = os.path.splitext(os.path.basename(file_path))[0]  # Extract base name of file
    output_dir = os.path.join(os.getcwd(), base_name)  # Set directory path
    os.makedirs(output_dir, exist_ok=True)  # Create the directory if it doesn't exist
    print(f"Output directory created at: {output_dir}")
    return output_dir

# Function to load, clean, analyze, and visualize the dataset.
def analyze_file(file_path, token):
    """Perform dataset analysis and generate outputs."""

    # Configure OpenAI API
    openai.api_base = "https://aiproxy.sanand.workers.dev/openai/v1"
    openai.api_key = token

    # Create an output directory for saving results
    output_dir = create_output_directory(file_path)

    # Identify file type based on the extension
    file_extension = os.path.splitext(file_path)[1].lower()
    print(f"Detected file type: {file_extension}")

    # Load the dataset based on its format
    try:
        if file_extension == ".csv":
            print("Loading CSV file...")
            try:
                data = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                print("UTF-8 decoding failed, trying ISO-8859-1...")
                data = pd.read_csv(file_path, encoding='ISO-8859-1')
        elif file_extension in [".xls", ".xlsx"]:
            print("Loading Excel file...")
            data = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format. Only CSV and Excel files are accepted.")
        print("Dataset loaded successfully.")
    except Exception as e:
        print(f"Error while loading dataset: {e}")
        raise

    # Clean the data
    try:
        print("Cleaning the dataset...")
        data.replace(r'^\s*$', np.nan, regex=True, inplace=True)  # Replace empty strings with NaN
    except Exception as e:
        print(f"Error during data cleaning: {e}")
        raise

    # Perform exploratory data analysis
    try:
        print("Analyzing the dataset...")
        summary_stats = data.describe(include="all")  # Generate descriptive statistics
        data_types = data.dtypes  # Get data types of all columns
        missing_values = data.isnull().sum()  # Count missing values per column
        missing_percentage = (missing_values / len(data)) * 100  # Calculate missing value percentage
        missing_report = pd.DataFrame({
            "Missing Values": missing_values,
            "Percentage": missing_percentage
        })

        # Detect outliers using the IQR method
        numeric_data = data.select_dtypes(include=[np.number])
        Q1 = numeric_data.quantile(0.25)
        Q3 = numeric_data.quantile(0.75)
        IQR = Q3 - Q1
        outliers = ((numeric_data < (Q1 - 1.5 * IQR)) | (numeric_data > (Q3 + 1.5 * IQR))).sum()

        # Generate visualizations
        print("Creating visualizations...")

        # Correlation matrix
        plt.figure(figsize=(10, 8))
        sns.heatmap(numeric_data.corr(), annot=True, cmap="coolwarm", fmt=".2f")
        plt.title("Correlation Matrix")
        plt.savefig(os.path.join(output_dir, "correlation_matrix.png"))
        plt.close()

        # Missing values heatmap
        plt.figure(figsize=(10, 6))
        sns.heatmap(data.isnull(), cbar=False, cmap="viridis")
        plt.title("Missing Values Heatmap")
        plt.savefig(os.path.join(output_dir, "missing_values_heatmap.png"))
        plt.close()

        # Boxplot for outliers
        plt.figure(figsize=(12, 8))
        sns.boxplot(data=numeric_data)
        plt.xticks(rotation=45)
        plt.title("Outlier Detection (Boxplot)")
        plt.savefig(os.path.join(output_dir, "outlier_boxplot.png"))
        plt.close()

        # Histograms for numerical features
        numeric_data.hist(figsize=(12, 10), bins=30)
        plt.suptitle("Histograms of Numerical Features")
        plt.savefig(os.path.join(output_dir, "numerical_histograms.png"))
        plt.close()

        # Bar Plot
        categorical_data = data.select_dtypes(include=['object'])
        for col in categorical_data.columns:
            top_categories = data[col].value_counts().nlargest(10)  # Get the top 10 categories
            plt.figure(figsize=(10, 6))
            sns.barplot(x=top_categories.values, y=top_categories.index, palette="viridis")
            plt.title(f"Top 10 Distribution of {col}")
            plt.xlabel("Count")
            plt.ylabel(col)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{col}_top10_distribution.png"))
            plt.close()

        

    except Exception as e:
        print(f"Error during analysis: {e}")
        raise

    # Generate narrative analysis using GPT
    
    try:
        narrative_prompt = f"""
You are a data analyst tasked with creating a comprehensive narrative for the dataset `{os.path.basename(file_path)}`. Summarize the insights, describe the data cleaning process, and highlight key patterns. Include findings from the visualizations generated.
"""

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": narrative_prompt}
            ],
            max_tokens=1000
        )

        narrative = response['choices'][0]['message']['content']

        # Save the narrative as a README file
        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write(narrative)
        print(f"Analysis report saved as {readme_path}")

    except Exception as e:
        print(f"Error generating narrative: {e}")
        raise

# Main execution logic
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a dataset and generate insights.")
    parser.add_argument("file_path", type=str, help="Path to the dataset file (CSV or Excel).")
    parser.add_argument("--token", type=str, help="API token for GPT (optional).")
    args = parser.parse_args()

    token = args.token if args.token else get_api_token()
    if not token:
        print("API token is required. Set it in an environment variable or pass it as an argument.")
        sys.exit(1)

    try:
        analyze_file(args.file_path, token)
        print("Analysis complete.")
    except Exception as e:
        print(f"An error occurred: {e}")


