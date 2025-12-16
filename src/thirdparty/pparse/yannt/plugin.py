def register(subparsers):
    p = subparsers.add_parser("pparse", help="Parse command")
    p.add_argument("--x", type=int, required=True)
    p.set_defaults(func=run)

def run(args):
    print("Running pparse command")