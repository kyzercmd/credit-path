import argparse
from app.data.generator import generate_dataset
from app.data.loader import save_data

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic data")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n_customers", type=int, default=10000, help="Number of customers")
    args = parser.parse_args()

    print(f"Generating data for {args.n_customers} customers...")
    data = generate_dataset(seed=args.seed, n_customers=args.n_customers)
    
    print("Saving data to disk...")
    save_data(data)
    
    print("Done!")

if __name__ == "__main__":
    main()
