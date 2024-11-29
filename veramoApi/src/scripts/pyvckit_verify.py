import sys

from pyvckit.verify import verify_vc


def main():
    if len(sys.argv) < 1:
        print(False)

    file_path = sys.argv[1]
    with open(file_path) as f:
        vc = f.read()
        
        print(verify_vc(vc))
        return
    
    print(False)
    return 


if __name__ == '__main__':
    main()
