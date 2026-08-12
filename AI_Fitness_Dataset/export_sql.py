import sys

from export_all import parser, run_export


if __name__ == "__main__":
    args = parser().parse_args()
    run_export(args, "sql")
    sys.exit(0)
