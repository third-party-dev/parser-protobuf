from __future__ import annotations

from typing import Any


class StackMark:


    def __init__(self, opcode: Any) -> None:
        self.opcode: Any = opcode


    def __repr__(self) -> str:
        return "**MARK**"


class PersistentCall:


    def __init__(self, id: Any, arg: Any, opcode: Any) -> None:
        self.id: Any = id
        self.arg: Any = arg
        self.opcode: Any = opcode


    def __repr__(self) -> str:
        return f"PERSID_CALL(\n  arg={self.arg}\n)"


    def pparse_repr(self, depth: int = 0, step: str = " ") -> str:
        from thirdparty.pparse.utils import pparse_repr

        res = ["PERSID_CALL(  # PERSID_CALL\n"]
        spacer = depth * step

        res.append(f"{spacer}{step}id: {self.id}\n")
        res.append(f"{spacer}{step}arg: ")
        res.append(f"{pparse_repr(self.arg, depth + 1, step)}")

        res.append(f"{spacer})")

        return "".join(res)


def try_decode_and_strip(val: Any) -> str:
    newval = val
    if isinstance(val, bytes):
        newval = val.decode("utf-8")
    return newval.strip()


class ReduceCall(dict):


    def __init__(self, module_call: tuple[bytes, bytes], arg: Any, opcode: Any) -> None:
        super().__init__()

        self.module_call: tuple[bytes, bytes] = module_call
        self.module: str = try_decode_and_strip(self.module_call[0])
        self.function: str = try_decode_and_strip(self.module_call[1])
        self.arg: Any = arg
        self.opcode: Any = opcode
        self.state: Any = None


    def __repr__(self) -> str:
        return (
            f"REDUCE_CALL(\n"
            f"  mod={self.module_call[0]},\n"
            f"  func={self.module_call[1]},\n"
            f"  arg={self.arg}\n"
            f"  state={self.state}\n"
            ")"
        )


    def pparse_repr(self, depth: int = 0, step: str = "  ") -> str:
        from thirdparty.pparse.utils import pparse_repr

        spacer = depth * step
        res = [
            # f'{spacer}# REDUCE_CALL\n',
            f"{self.module}.{self.function}(\n",
        ]

        res.append(f"{spacer}{step}*(  # ARG\n")
        res.append(f"{spacer}{step}{step}")
        res.append(pparse_repr(self.arg, depth + 2, step))
        res.append(f"{spacer}{step})  # End of ARG\n")

        res.append(f"\n{spacer}{step}# STATE\n")
        res.append(f"{spacer}{step}")
        res.append(pparse_repr(self.state, depth + 1, step))

        res.append(f"\n{spacer}{step}# ITEMS\n")
        res.append(f"{spacer}{step}")
        res.append(pparse_repr(dict(self), depth + 1, step))

        res.append(f"{spacer})")

        return "".join(res)

    # def dump(self, depth=0, step=2, dumper=None):

    #     if not dumper:
    #         dumper = Dumper.default()
    #     dumper.dump("ReduceCall", self._value, '', depth=depth, step=step)


class NewCall(dict):


    def __init__(self, module_call: tuple[bytes, bytes], arg: Any, opcode: Any) -> None:
        super().__init__()

        self.module_call: tuple[bytes, bytes] = module_call
        self.module: str = self.module_call[0].decode("utf-8").strip()
        self.function: str = self.module_call[1].decode("utf-8").strip()
        self.arg: Any = arg
        self.opcode: Any = opcode
        self.state: Any = None


    def __repr__(self) -> str:
        return (
            f"NEW_CALL(\n"
            f"  mod={self.module_call[0]},\n"
            f"  func={self.module_call[1]},\n"
            f"  arg={self.arg}\n"
            f"  state={self.state}\n"
            ")"
        )


    def pparse_repr(self, depth: int = 0, step: str = "  ") -> str:
        from thirdparty.pparse.utils import pparse_repr

        spacer = depth * step
        res = [
            # f'{spacer}# NEW_CALL\n',
            f"{self.module}.{self.function}(\n",
        ]

        res.append(f"{spacer}{step}*(  # ARG\n")
        res.append(f"{spacer}{step}{step}")
        res.append(pparse_repr(self.arg, depth + 2, step))
        res.append(f"{spacer}{step})  # End of ARG\n")

        res.append(f"\n{spacer}{step}# STATE\n")
        res.append(f"{spacer}{step}")
        res.append(pparse_repr(self.state, depth + 1, step))

        res.append(f"\n{spacer}{step}# ITEMS\n")
        res.append(f"{spacer}{step}")
        res.append(pparse_repr(dict(self), depth + 1, step))

        res.append(f"{spacer})")

        return "".join(res)
