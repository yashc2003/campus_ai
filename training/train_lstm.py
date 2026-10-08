import sys
from training.train_rnn import main

if __name__ == "__main__":
    sys.argv[1:1] = ["--model", "lstm"]
    main()
