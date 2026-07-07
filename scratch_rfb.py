import os

dir_mei = r"C:\Users\herbe\PycharmProjects\pythonProject2\MEI"

def print_first_lines(filename, n=3):
    path = os.path.join(dir_mei, filename)
    print(f"\n--- {filename} ---")
    try:
        with open(path, 'r', encoding='latin1') as f:
            for _ in range(n):
                line = f.readline()
                print(line.strip())
    except Exception as e:
        print(f"Error: {e}")

print_first_lines("K3241.K03200Y0.D60314.ESTABELE", 1)
print_first_lines("F.K03200$Z.D60314.MUNICCSV", 3)
print_first_lines("F.K03200$Z.D60314.CNAECSV", 3)
