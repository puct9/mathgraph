import functools
import math
from typing import List

import pydot


def convert_variable(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        args = [
            Constant(x) if not isinstance(x, Variable) else x for x in args
        ]
        kwargs = {
            k: Constant(v) if not isinstance(v, Variable) else v
            for k, v in kwargs.items()
        }
        return fn(*args, **kwargs)

    return wrapped


def prefer_return_const(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        self: Variable = args[0]
        e = self.evaluate()
        if isinstance(e, Constant):
            return e
        return fn(*args, **kwargs)

    return wrapped


class Variable:
    ALPHABET = "ab"

    def __init__(self, *args):
        self.a: Variable
        self.b: Variable
        if len(args) > 2:
            raise ValueError(f"Only support {len(self.ALPHABET)} arguments")
        for char, val in zip(Variable.ALPHABET, args):
            if isinstance(val, Variable):
                setattr(self, char, val)
            else:
                setattr(self, char, Constant(val))

    def __add__(self, other) -> "Variable":
        return Add(self, other)

    def __radd__(self, other) -> "Variable":
        return Add(other, self)

    def __sub__(self, other) -> "Variable":
        return Subtract(self, other)

    def __neg__(self) -> "Variable":
        return 0 - self

    def __rsub__(self, other) -> "Variable":
        return Subtract(other, self)

    def __mul__(self, other) -> "Variable":
        return Multiply(self, other)

    def __rmul__(self, other) -> "Variable":
        return Multiply(other, self)

    def __pow__(self, other) -> "Variable":
        return Power(self, other)

    def __rpow__(self, other) -> "Variable":
        return Power(other, self)

    def __truediv__(self, other) -> "Variable":
        return Divide(self, other)

    def __rtruediv__(self, other) -> "Variable":
        return Divide(other, self)

    def __call__(self, **values) -> "Variable":
        return self.evaluate(**values)

    @property
    def inputs(self) -> List["Variable"]:
        res = []
        for char in Variable.ALPHABET:
            if not hasattr(self, char):
                break
            res.append(getattr(self, char))
        return res

    def visualise(self) -> pydot.Dot:
        graph = pydot.Dot(
            "visualisation", graph_type="digraph", bgcolor="white"
        )
        self._visualise(graph, "f")
        return graph

    def _visualise(self, graph: pydot.Dot, name: str, prev: str = "") -> None:
        node_name = f"{prev}-{name}" if prev else name
        if prev:
            graph.add_node(
                pydot.Node(
                    node_name, label=f"{self.description()} [input {name}]"
                )
            )
        else:
            graph.add_node(
                pydot.Node(
                    node_name, label=f"{self.description()} [output {name}]"
                )
            )
        if prev:
            graph.add_edge(pydot.Edge(node_name, prev))
        for char, inp in zip(Variable.ALPHABET, self.inputs):
            inp._visualise(graph, char, node_name)

    def description(self) -> str:
        return self.__class__.__name__

    def simplified(self) -> "Variable":
        raise NotImplementedError

    def evaluate(self, **values) -> "Variable":
        raise NotImplementedError

    def gradient(self, name) -> "Variable":
        raise NotImplementedError


class Constant(Variable):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def __repr__(self) -> str:
        return f"Constant({self.value})"

    @convert_variable
    def __add__(self, other) -> "Variable":
        if isinstance(other, Constant):
            return Constant(self.value + other.value)
        return super().__add__(other)

    @convert_variable
    def __radd__(self, other) -> "Variable":
        if isinstance(other, Constant):
            return Constant(other.value + self.value)
        return super().__radd__(other)

    @convert_variable
    def __sub__(self, other) -> "Variable":
        if isinstance(other, Constant):
            return Constant(self.value - other.value)
        return super().__sub__(other)

    @convert_variable
    def __rsub__(self, other) -> "Variable":
        if isinstance(other, Constant):
            return Constant(other.value - self.value)
        return super().__rsub__(other)

    @convert_variable
    def __mul__(self, other) -> "Variable":
        if isinstance(other, Constant):
            return Constant(self.value * other.value)
        return super().__mul__(other)

    @convert_variable
    def __rmul__(self, other) -> "Variable":
        if isinstance(other, Constant):
            return Constant(other.value * self.value)
        return super().__rmul__(other)

    @convert_variable
    def __pow__(self, other) -> "Variable":
        if isinstance(other, Constant):
            return Constant(self.value**other.value)
        return super().__pow__(other)

    @convert_variable
    def __rpow__(self, other) -> "Constant":
        if isinstance(other, Constant):
            return Constant(other.value**self.value)
        return super().__rpow__(other)

    @convert_variable
    def __truediv__(self, other) -> "Constant":
        if isinstance(other, Constant):
            return Constant(self.value / other.value)
        return super().__truediv__(other)

    @convert_variable
    def __rtruediv__(self, other) -> "Constant":
        if isinstance(other, Constant):
            return Constant(other.value / self.value)
        return super().__rtruediv__(other)

    def simplified(self):
        return Constant(self.value)

    def description(self):
        return super().description() + f": {self.value}"

    def evaluate(self, **values):
        return Constant(self.value)

    def gradient(self, name):
        return Constant(0)


class Input(Variable):
    def __init__(self, name):
        super().__init__()
        self.name: str = name

    def simplified(self):
        return Input(self.name)

    def description(self):
        return super().description() + f': "{self.name}"'

    def evaluate(self, **values):
        return values.get(self.name, self)

    def gradient(self, name):
        return int(self.name == name)


class Operation(Variable):
    pass


class Add(Operation):
    def __init__(self, a, b):
        super().__init__(a, b)

    @prefer_return_const
    def simplified(self):
        a, b = self.a.simplified(), self.b.simplified()
        if isinstance(a, Constant) and a.value == 0:
            return b
        elif isinstance(b, Constant) and b.value == 0:
            return a

        # Addition simplification rules
        # 2 constants: handled by @prefer_return_const

        # Constant + Variable:
        # 2     x       x     2
        #  \   /   -->   \   /
        #   add           add
        if isinstance(a, Constant):
            a, b = b, a

        # Variable (a) must be Add with attached Constant (a.b)
        if not (isinstance(a, Add) and isinstance(a.b, Constant)):
            return a + b

        # Add + Constant: Simplify
        # x     2
        #  \   /
        #   add     3  -->  x     5
        #      \   /         \   /
        #       add           add
        if isinstance(b, Constant):
            return a.a + (a.b + b).evaluate()

        # Final case:
        # Add * Variable: "Lower"
        # x     2           x     y
        #  \   /             \   /
        #   add     y  -->    add     2
        #      \   /             \   /
        #       add               add
        return a.a + b + a.b

    def evaluate(self, **values):
        a = self.a.evaluate(**values)
        b = self.b.evaluate(**values)
        vs = a, b
        for i, v in enumerate(vs):
            if isinstance(v, Constant) and v.value == 0:
                return vs[1 - i]
        return a + b

    def gradient(self, name):
        return self.a.gradient(name) + self.b.gradient(name)


class Subtract(Operation):
    def __init__(self, a, b):
        super().__init__(a, b)

    @prefer_return_const
    def simplified(self):
        a, b = self.a.simplified(), self.b.simplified()
        if isinstance(b, Constant) and b.value == 0:
            return a
        return a - b

    def evaluate(self, **values):
        return self.a.evaluate(**values) - self.b.evaluate(**values)

    def gradient(self, name):
        return self.a.gradient(name) - self.b.gradient(name)


class Multiply(Operation):
    def __init__(self, a, b):
        super().__init__(a, b)
        self.a: Variable
        self.b: Variable

    @prefer_return_const
    def simplified(self):
        # Simple optimisation
        a, b = self.a.simplified(), self.b.simplified()
        vs = [a, b]
        for i, v in enumerate(vs):
            if isinstance(v, Constant):
                if v.value == 0:
                    return v
                if v.value == 1:
                    return vs[1 - i]

        # Multiplication simplification rules
        # 2 constants: handled by @prefer_return_const

        # Constant * Variable:
        # 2     x       x     2
        #  \   /   -->   \   /
        #   mul           mul
        if isinstance(a, Constant):
            a, b = b, a

        # Variable (a) must be Multiply with attached Constant (a.b)
        if not (isinstance(a, Multiply) and isinstance(a.b, Constant)):
            return a * b

        # Multiply * Constant: Simplify
        # x     2
        #  \   /
        #   mul     3  -->  x     6
        #      \   /         \   /
        #       mul           mul
        if isinstance(b, Constant):
            return a.a * (a.b * b).evaluate()

        # Final case:
        # Multiply * Variable: "Lower"
        # x     2           x     y
        #  \   /             \   /
        #   mul     y  -->    mul     2
        #      \   /             \   /
        #       mul               mul
        return a.a * b * a.b

    def evaluate(self, **values):
        a = self.a.evaluate(**values)
        b = self.b.evaluate(**values)
        vs = a, b
        for i, v in enumerate(vs):
            if isinstance(v, Constant) and v.value == 0:
                return Constant(0)
            if isinstance(v, Constant) and v.value == 1:
                return vs[1 - i]
        return a * b

    def gradient(self, name):
        # d/dx(a b) = a b' + a' b
        a_db = self.a * self.b.gradient(name)
        b_da = self.a.gradient(name) * self.b
        return a_db + b_da


class Power(Operation):
    def __init__(self, a, b):
        super().__init__(a, b)
        self.a: Variable
        self.b: Variable

    @prefer_return_const
    def simplified(self):
        a, b = self.a.simplified(), self.b.simplified()
        if isinstance(b, Constant):
            if b.value == 0:
                return Constant(1)
            if b.value == 1:
                return a
        # Optimise (x^b)^c -> x^(b*c) where b and c are constants
        # We only need to optimise the case as subsequent simplifications will
        # take care of longer chains
        # Example:
        # x     2
        #  \   /
        #   pow     3  -->  x     6
        #      \   /         \   /
        #       pow           pow

        # If b and c are not both constants, then the constant should be
        # "lowered"
        # Example:
        # x     2           x     y
        #  \   /             \   /
        #   pow     y  -->    pow     2
        #      \   /             \   /
        #       pow               pow

        if isinstance(a, Power):
            other_a, other_b = a.inputs
            if isinstance(other_b, Constant):
                if isinstance(b, Constant):
                    return other_a ** (b * other_b).evaluate()
                else:
                    return (other_a**b) ** other_b

        return a**b

    def evaluate(self, **values):
        exponent = self.b.evaluate(**values)
        # Necessary for simplify()
        if isinstance(exponent, Constant):
            if exponent.value == 0:
                return Constant(1)
            elif exponent.value == 1:
                return self.a.evaluate(**values)
        return self.a.evaluate(**values) ** self.b.evaluate(**values)

    def gradient(self, name):
        # d/dx(a^b) = a^(b-1) (b a' + a log(a) b')
        return self.a ** (self.b - 1) * (
            self.b * self.a.gradient(name)
            + self.a * Log(self.a) * self.b.gradient(name)
        )


class Divide(Operation):
    def __init__(self, a, b):
        super().__init__(a, b)

    def simplified(self):
        a, b = self.a.simplified(), self.b.simplified()
        if isinstance(a, Constant) and a.value == 0:
            return Constant(0)
        if isinstance(b, Constant) and b.value == 1:
            return a
        return a / b

    def evaluate(self, **values):
        return self.a.evaluate(**values) / self.b.evaluate(**values)

    def gradient(self, name):
        # d/dx(a / b) = (a' b - a b') / b^2
        da_b = self.a.gradient(name) * self.b
        a_db = self.a * self.b.gradient(name)
        return (da_b - a_db) / self.b**2


class Log(Operation):
    ALPHABET = "a"

    def __init__(self, a):
        super().__init__(a)

    def simplified(self) -> "Variable":
        return Log(self.a.simplified())

    def evaluate(self, **values) -> "Variable":
        v = self.a.evaluate(**values)
        if isinstance(v, Constant):
            return Constant(math.log(v.value))
        else:
            return v

    def gradient(self, name) -> "Variable":
        # d/dx(log(a)) = a' / a
        return self.a.gradient(name) / self.a
