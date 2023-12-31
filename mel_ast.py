from abc import ABC, abstractmethod
from typing import Callable, Tuple, Optional, Union, List, cast
from enum import Enum
from semantic import IdentScope, TypeDesc, TYPE_CONVERTIBILITY, BinOp, IdentDesc, SemanticException, \
    BIN_OP_TYPE_COMPATIBILITY, ScopeType, BaseType


class AstNode(ABC):
    init_action: Callable[['AstNode'], None] = None

    def __init__(self, column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__()
        self.column = column
        self.line = line
        for k, v in props.items():
            setattr(self, k, v)
        if AstNode.init_action is not None:
            AstNode.init_action(self)
        self.node_type: Optional[TypeDesc] = None
        self.node_ident: Optional[IdentDesc] = None

    @property
    def childs(self) -> Tuple['AstNode', ...]:
        return ()

    @abstractmethod
    def __str__(self) -> str:
        pass

    def to_str(self):
        return str(self)

    def to_str_full(self):
        r = ''
        if self.node_ident:
            r = str(self.node_ident)
        elif self.node_type:
            r = str(self.node_type)
        return self.to_str() + (' : ' + r if r else '')

    def semantic_error(self, message: str):
        raise SemanticException(message, self.line, self.column)

    def semantic_check(self, scope: IdentScope) -> None:
        pass

    def msil_gen(self, generator) -> None:
        generator.msil_gen(self)

    @property
    def tree(self) -> [str, ...]:
        res = [self.to_str_full()]
        childs_temp = self.childs
        for i, child in enumerate(childs_temp):
            ch0, ch = '├', '│'
            if i == len(childs_temp) - 1:
                ch0, ch = '└', ' '
            res.extend(((ch0 if j == 0 else ch) + ' ' + s for j, s in enumerate(child.tree)))
        return res

    def visit(self, func: Callable[['AstNode'], None]) -> None:
        func(self)
        map(func, self.childs)

    def __getitem__(self, index):
        return self.childs[index] if index < len(self.childs) else None


class ExprNode(AstNode):
    pass


class LiteralNode(ExprNode):
    def __init__(self, literal: str,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.literal = literal
        if literal in ('true', 'false'):
            self.value = bool(literal)
        else:
            self.value = eval(literal)

    def __str__(self) -> str:
        return self.literal

    def semantic_check(self, scope: IdentScope) -> None:
        if isinstance(self.value, bool):
            self.node_type = TypeDesc(base_type_=BaseType.BOOL)
        # проверка должна быть позже bool, т.к. bool наследник от int
        elif isinstance(self.value, int):
            self.node_type = TypeDesc(base_type_=BaseType.INT)
        elif isinstance(self.value, float):
            self.node_type = TypeDesc(base_type_=BaseType.FLOAT)
        elif isinstance(self.value, str):
            self.node_type = TypeDesc(base_type_=BaseType.STR)
        else:
            self.semantic_error('Неизвестный тип {} для {}'.format(type(self.value), self.value))


class IdentNode(ExprNode):
    def __init__(self, name: str,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.name = str(name)

    def __str__(self) -> str:
        return str(self.name)

    def semantic_check(self, scope: IdentScope) -> None:
        ident = scope.get_ident(self.name)
        if ident is None:
            self.semantic_error('Идентификатор {} не найден'.format(self.name))
        self.node_type = ident.type
        self.node_ident = ident


class Bools(Enum):
    TRUE = 'true'
    FALSE = 'false'

    def __str__(self):
        return self.value


class BinOpNode(ExprNode):
    def __init__(self, op: BinOp, arg1: ExprNode, arg2: ExprNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2

    @property
    def childs(self) -> Tuple[ExprNode, ExprNode]:
        return self.arg1, self.arg2

    def __str__(self) -> str:
        return str(self.op.value)

    def semantic_check(self, scope: IdentScope) -> None:
        self.arg1.semantic_check(scope)
        self.arg2.semantic_check(scope)
        if self.arg1.node_type.is_array and self.arg2.node_type.is_array:
            self.node_type = TypeDesc(base_type_=BaseType.BOOL)
            return

        elif self.arg1.node_type.is_simple or self.arg2.node_type.is_simple:
            compatibility = BIN_OP_TYPE_COMPATIBILITY[self.op]
            args_types = (self.arg1.node_type.base_type, self.arg2.node_type.base_type)
            if args_types in compatibility:
                self.node_type = TypeDesc.from_base_type(compatibility[args_types])
                return

            if self.arg2.node_type.base_type in TYPE_CONVERTIBILITY:
                for arg2_type in TYPE_CONVERTIBILITY[self.arg2.node_type.base_type]:
                    args_types = (self.arg1.node_type.base_type, arg2_type)
                    if args_types in compatibility:
                        self.arg2 = type_convert(self.arg2, TypeDesc.from_base_type(arg2_type))
                        self.node_type = TypeDesc.from_base_type(compatibility[args_types])
                        return
            if self.arg1.node_type.base_type in TYPE_CONVERTIBILITY:
                for arg1_type in TYPE_CONVERTIBILITY[self.arg1.node_type.base_type]:
                    args_types = (arg1_type, self.arg2.node_type.base_type)
                    if args_types in compatibility:
                        self.arg1 = type_convert(self.arg1, TypeDesc.from_base_type(arg1_type))
                        self.node_type = TypeDesc.from_base_type(compatibility[args_types])
                        return
        # if self.arg1.node_type.is_array and self.arg2.node_type.is_array:

        self.semantic_error("Оператор {} не применим к типам ({}, {})".format(
            self.op, self.arg1.node_type, self.arg2.node_type
        ))


class StmtNode(ExprNode):

    def to_str_full(self):
        return self.to_str()


class TypeNode(StmtNode):
    def __init__(self, name: IdentNode, innerType: Optional[AstNode],
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.name = name
        self.innerType = innerType

    @property
    def childs(self) -> Tuple:
        return ()

    @property
    def type_desc(self) -> Tuple:
        return ()

    def __str__(self) -> str:
        return self.getStrView()

    def semantic_check(self, scope: IdentScope) -> None:
        if self.name is None:
            self.semantic_error('Неизвестный тип {}'.format(self.name))
        (lvl, base_type) = self.getInnerTypes(0)
        try:
            self.node_type = TypeDesc(base_type_=BaseType(base_type.name), array_level=lvl)
        except:
            self.semantic_error("Несуществующий тип " + base_type.name)

    def getInnerTypes(self, level: int) -> Tuple[int, IdentNode]:
        if self.innerType is not None:
            node: TypeNode = cast(TypeNode, self.innerType)
            return node.getInnerTypes(level + 1)
        return level, self.name

    def getStrView(self) -> str:
        deep, typeName = self.getInnerTypes(0)
        begin = ''
        end = ''
        if deep == 0:
            return self.name.__str__()
        for i in range(deep):
            begin += 'Array<'
            end += '>'
        return begin + typeName.__str__() + end


class CallNode(StmtNode):
    def __init__(self, func: IdentNode, *params: Tuple[ExprNode],
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.func = func
        self.params = params

    @property
    def childs(self) -> Tuple[IdentNode, ...]:
        # return self.func, (*self.params)
        return (self.func,) + self.params

    def __str__(self) -> str:
        return 'call'

    def semantic_check(self, scope: IdentScope) -> None:
        func = scope.get_ident(self.func.name)
        if func is None:
            self.semantic_error('Функция {} не найдена'.format(self.func.name))
        if not func.type.func:
            self.semantic_error('Идентификатор {} не является функцией'.format(func.name))
        if len(func.type.params) != len(self.params):
            self.semantic_error('Кол-во аргументов {} не совпадает (ожидалось {}, передано {})'.format(
                func.name, len(func.type.params), len(self.params)
            ))
        params = []
        error = False
        decl_params_str = fact_params_str = ''
        for i in range(len(self.params)):
            param: ExprNode = self.params[i]
            param.semantic_check(scope)
            if len(decl_params_str) > 0:
                decl_params_str += ', '
            decl_params_str += str(func.type.params[i])
            if len(fact_params_str) > 0:
                fact_params_str += ', '
            fact_params_str += str(param.node_type)
            try:
                params.append(type_convert(param, func.type.params[i]))
            except:
                error = True
        if error:
            self.semantic_error('Фактические типы ({1}) аргументов функции {0} не совпадают с формальными ({2})\
                                    и не приводимы'.format(
                func.name, fact_params_str, decl_params_str
            ))
        else:
            self.params = tuple(params)
            self.func.node_type = func.type
            self.func.node_ident = func
            self.node_type = func.type.return_type


class AssignNode(StmtNode):
    def __init__(self, var: IdentNode, val: ExprNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.var = var
        self.column = var.column
        self.line = var.line
        self.val = val

    @property
    def childs(self) -> Tuple[IdentNode, ExprNode]:
        return self.var, self.val

    def __str__(self) -> str:
        return '='

    def semantic_check(self, scope: IdentScope) -> None:
        self.var.semantic_check(scope)
        self.val.semantic_check(scope)
        if isinstance(self.val, EmptyArrNode):
            if self.var.node_type.is_array:
                self.val.node_type = self.var.node_type
            else:
                self.semantic_error("Нельзя присвоить типу " + self.var.node_type.base_type.name + " тип массива")
        self.val = type_convert(self.val, self.var.node_type, self, 'присваиваемое значение')
        self.node_type = self.var.node_type


class SingleIfNode(StmtNode):
    def __init__(self, cond: ExprNode, then_stmt: StmtNode, else_stmt: Optional[StmtNode] = None,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.cond = cond
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

    @property
    def childs(self) -> Tuple[ExprNode, StmtNode, Optional[StmtNode]]:
        return (self.cond, self.then_stmt) + (self.else_stmt,) if self.else_stmt else ()

    def __str__(self) -> str:
        return 'if'

    def semantic_check(self, scope: IdentScope) -> None:
        self.cond.semantic_check(scope)
        self.cond = type_convert(self.cond, TypeDesc(base_type_=BaseType.BOOL), None, 'условие')
        self.then_stmt.semantic_check(IdentScope(scope))
        if self.else_stmt:
            self.else_stmt.semantic_check(IdentScope(scope))
        self.node_type = TypeDesc(base_type_=BaseType.VOID)


class MultiIfNode(StmtNode):
    def __init__(self, cond: ExprNode, then_stmt: StmtNode, else_stmt: StmtNode = None,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.cond = cond
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

    @property
    def childs(self) -> Tuple[ExprNode, StmtNode, Optional[StmtNode]]:
        return self.cond, self.then_stmt, self.else_stmt

    def __str__(self) -> str:
        return 'if'

    def semantic_check(self, scope: IdentScope) -> None:
        self.cond.semantic_check(scope)
        self.cond = type_convert(self.cond, TypeDesc(base_type_=BaseType.BOOL), None, 'условие')
        self.then_stmt.semantic_check(IdentScope(scope))
        self.else_stmt.semantic_check(scope)
        self.node_type = TypeDesc(base_type_=BaseType.VOID)


class StmtListNode(StmtNode):
    def __init__(self, *exprs: StmtNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.exprs = exprs
        self.program = False

    @property
    def childs(self) -> Tuple[StmtNode, ...]:
        return self.exprs

    def __str__(self) -> str:
        return '...'

    def semantic_check(self, scope: IdentScope) -> None:
        if not self.program:
            scope = IdentScope(scope)
        for expr in self.exprs:
            expr.semantic_check(scope)
        self.node_type = TypeDesc(base_type_=BaseType.VOID)


class WhenInnerNode(StmtNode):
    def __init__(self, expr: ExprNode, stmt: StmtNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.expr = expr
        self.stmt = stmt

    @property
    def childs(self) -> Tuple[ExprNode, StmtNode]:
        return self.expr, self.stmt

    def __str__(self) -> str:
        return '->'

    def semantic_check(self, scope: IdentScope) -> None:
        self.expr.semantic_check(scope)
        self.stmt.semantic_check(IdentScope(scope))
        self.node_type = TypeDesc(base_type_=BaseType.VOID)


class WhenNode(StmtNode):
    def __init__(self, ident: IdentNode, optionalblocks: List[WhenInnerNode], finalBlock: StmtListNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.ident = ident
        self.optionalblocks = optionalblocks
        self.finalBlock = finalBlock

    @property
    def childs(self) -> Tuple[StmtNode, ...]:
        return self.ident, *self.optionalblocks, self.finalBlock

    def __str__(self) -> str:
        return 'when'

    def semantic_check(self, scope: IdentScope) -> None:
        self.ident.semantic_check(scope)
        for i in self.optionalblocks:
            i.semantic_check(IdentScope(scope))
            if self.ident.node_type != i.expr.node_type:
                self.semantic_error("неверный тип в when")
        self.finalBlock.semantic_check(IdentScope(scope))
        self.node_type = TypeDesc(base_type_=BaseType.VOID)


class TypeConvertNode(ExprNode):
    """Класс для представления в AST-дереве операций конвертации типов данных
       (в языке программирования может быть как expression, так и statement)
    """

    def __init__(self, expr: ExprNode, type_: TypeDesc,
                 column: Optional[int] = None, line: Optional[int] = None, **props) -> None:
        super().__init__(column=column, line=line, **props)
        self.expr = expr
        self.type = type_
        self.node_type = type_

    def __str__(self) -> str:
        return 'convert'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return IdentNode(str(self.type)), self.expr


def type_convert(expr: ExprNode, type_: TypeDesc, except_node: Optional[AstNode] = None,
                 comment: Optional[str] = None) -> ExprNode:
    """Метод преобразования ExprNode узла AST-дерева к другому типу
    :param expr: узел AST-дерева
    :param type_: требуемый тип
    :param except_node: узел, о которого будет исключение
    :param comment: комментарий
    :return: узел AST-дерева c операцией преобразования
    """

    if expr.node_type is None:
        except_node.semantic_error('Тип выражения не определен')
    if expr.node_type == type_:
        return expr
    if expr.node_type.is_simple and type_.is_simple and not expr.node_type.is_array and not type_.is_array and \
            expr.node_type.base_type in TYPE_CONVERTIBILITY and type_.base_type in TYPE_CONVERTIBILITY[
        expr.node_type.base_type]:
        return TypeConvertNode(expr, type_, expr.column, expr.line)
    else:
        (except_node if except_node else expr).semantic_error('Тип {0}{2} не конвертируется в {1}'.format(
            expr.node_type, type_, ' ({})'.format(comment) if comment else ''
        ))


class ReturnNode(StmtNode):
    """Класс для представления в AST-дереве оператора return
    """

    def __init__(self, val: ExprNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props) -> None:
        super().__init__(column=column, line=line, **props)
        self.column = val.column
        self.line = val.line
        self.val = val

    def __str__(self) -> str:
        return 'return'

    @property
    def childs(self) -> Tuple[ExprNode]:
        return self.val,

    def semantic_check(self, scope: IdentScope) -> None:
        self.val.semantic_check(IdentScope(scope))
        func = scope.curr_func
        if func is None:
            self.semantic_error('Оператор return применим только к функции')
        self.val = type_convert(self.val, func.func.type.return_type, self, 'возвращаемое значение')
        self.node_type = TypeDesc(base_type_=BaseType.VOID)


class VarTypeNode(StmtNode):
    def __init__(self, var: IdentNode, _type: TypeNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.var = var
        self.type = _type
        self.curr_scope = ScopeType.GLOBAL

    @property
    def childs(self) -> Tuple:
        return ()

    def set_param_scope(self) -> None:
        self.curr_scope = ScopeType.PARAM

    def __str__(self) -> str:
        return self.var.name + ':' + str(self.type)

    def semantic_check(self, scope: IdentScope) -> None:
        self.type.semantic_check(scope)
        self.var.node_type = self.type.node_type
        self.node_type = self.type.node_type
        self.var.node_ident = scope.add_ident(IdentDesc(self.var.name, self.type.node_type, self.curr_scope))


class VarInitNode(StmtNode):
    def __init__(self, varType: VarTypeNode, val: ExprNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.varType = varType
        self.val = val

    @property
    def childs(self) -> Tuple[VarTypeNode, ExprNode]:
        return self.varType, self.val

    def __str__(self) -> str:
        return 'var'

    def semantic_check(self, scope: IdentScope) -> None:
        self.varType.semantic_check(scope)
        self.val.semantic_check(scope)
        if isinstance(self.val, EmptyArrNode):
            if self.varType.node_type.is_array:
                self.val.node_type = self.varType.node_type
            else:
                self.semantic_error("Нельзя присвоить типу " + self.varType.node_type.base_type.name + " тип массива")
        if self.varType.node_type != self.val.node_type:
            self.semantic_error("неверное присвоение типа")


class WhileNode(StmtNode):
    def __init__(self, cond: ExprNode, body: StmtListNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.cond = cond
        self.body = body

    @property
    def childs(self) -> Tuple[ExprNode, StmtListNode]:
        return self.cond, self.body

    def __str__(self) -> str:
        return 'while'

    def semantic_check(self, scope: IdentScope) -> None:
        scope_inner = IdentScope(scope)
        self.cond.semantic_check(scope)
        self.cond = type_convert(self.cond, TypeDesc(base_type_=BaseType.BOOL), None, 'условие')
        self.body.semantic_check(scope_inner)
        self.node_type = TypeDesc(base_type_=BaseType.VOID)


class CommonFunDeclrNode(StmtNode):
    def __init__(self, name: IdentNode, retType: TypeNode, body: StmtListNode, params: Tuple[VarTypeNode, ...],
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.params = params
        self.name = name
        self.retType = retType
        self.body = body

    @property
    def childs(self) -> Tuple[StmtListNode]:
        return self.body,

    def __str__(self) -> str:
        return 'fun ' + self.name.name + '(' + self.strParams() + ')' + self.strRetVal()

    def strParams(self) -> str:
        s: str = ''
        for i in self.params:
            s += i.__str__()
            s += ', '
        return s[:-2] if s != '' else ''

    def strRetVal(self) -> str:
        return ': ' + str(self.retType)

    def semantic_check(self, scope: IdentScope) -> None:
        if scope.curr_func:
            self.semantic_error(
                "Объявление функции ({}) внутри другой функции не поддерживается".format(self.name.name))
        parent_scope = scope
        self.retType.semantic_check(scope)
        scope_inner = IdentScope(scope)

        # временно хоть какое-то значение, чтобы при добавлении параметров находить scope функции
        scope_inner.func = IdentDesc('', TypeDesc(base_type_=BaseType.VOID))
        params = []
        for param in self.params:
            # при проверке параметров происходит их добавление в scope
            param.set_param_scope()
            param.semantic_check(scope_inner)
            params.append(param.type.node_type)

        type_ = TypeDesc(None, self.retType.node_type, params=tuple(params))
        func_ident = IdentDesc(self.name.name, type_)
        scope_inner.func = func_ident
        self.name.node_type = type_
        try:
            self.name.node_ident = parent_scope.curr_global.add_ident(func_ident)
        except SemanticException as e:
            self.name.semantic_error("Повторное объявление функции {}".format(self.name.name))
        self.body.semantic_check(scope_inner)
        self.node_type = TypeDesc(base_type_=BaseType.VOID)


class ForArrNode(StmtNode):
    def __init__(self, param: IdentNode, arr: IdentNode, body: StmtListNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.param = param
        self.body = body
        self.arr = arr

    @property
    def childs(self) -> Tuple[IdentNode, IdentNode, StmtListNode]:
        return self.param, self.arr, self.body

    def __str__(self) -> str:
        return 'for ' + self.param.name + ' in ' + self.arr.name

    def semantic_check(self, scope: IdentScope) -> None:
        self.arr.semantic_check(scope)
        scope_inner = IdentScope(scope)
        if self.arr.node_type.array_level < 1:
            self.semantic_error(self.arr.name + " не является массивом")
        self.param.node_type = TypeDesc(base_type_=self.arr.node_type.base_type,
                                        array_level=self.arr.node_type.array_level - 1)
        self.param.node_ident = scope_inner.add_ident(IdentDesc(self.param.name, self.param.node_type, ScopeType.LOCAL))
        self.body.semantic_check(scope_inner)


class ForRangeNode(StmtNode):
    def __init__(self, param: IdentNode, start: LiteralNode, end: LiteralNode, body: StmtListNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.param = param
        self.body = body
        self.start = start
        self.end = end

    @property
    def childs(self) -> Tuple[IdentNode, StmtListNode]:
        return self.param, self.body

    def __str__(self) -> str:
        return 'for ' + self.param.name + ' in ' + self.start.__str__() + '..' + self.end.__str__()

    def semantic_check(self, scope: IdentScope) -> None:
        scope_inner = IdentScope(scope)
        self.start.semantic_check(scope)
        self.end.semantic_check(scope)
        if self.start.node_type == TypeDesc(base_type_=BaseType.INT) and self.end.node_type == TypeDesc(
                base_type_=BaseType.INT):
            if self.start.value > self.end.value:
                self.semantic_error("Неверно задан диапозон для for")
            else:
                self.param.node_type = TypeDesc(base_type_=BaseType.INT, array_level=0)
                self.param.node_ident = scope_inner.add_ident(
                    IdentDesc(self.param.name, TypeDesc(base_type_=BaseType.INT), ScopeType.LOCAL))
        else:
            self.semantic_error("Неверно введены параметры для for")
        self.body.semantic_check(scope_inner)


class EmptyArrNode(StmtNode):
    def __init__(self, size: int,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.size = size

    @property
    def childs(self) -> Tuple:
        return ()

    def __str__(self) -> str:
        return 'Array(' + str(self.size) + ')'

    def semantic_check(self, scope: IdentScope) -> None:
        if self.size.value < 1:
            self.semantic_error("Нельзя создать массив размером 0")


class ArrOfNode(StmtNode):
    def __init__(self, *params: ExprNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.params = params

    @property
    def childs(self) -> Tuple[ExprNode, ...]:
        return self.params

    def __str__(self) -> str:
        return 'arrayOf'

    def semantic_check(self, scope: IdentScope) -> None:
        for i in self.params:
            i.semantic_check(scope)
        if len(self.params) == 0:
            self.semantic_error("В массиве отсутствуют элементы")
        prev = self.params[0]
        for i in self.params:
            if i.node_type != prev.node_type:
                self.semantic_error(
                    "Типы элементов массива " + str(prev.node_type) + " и " + str(i.node_type) + " не совпадают")
        self.node_type = TypeDesc(base_type_=prev.node_type.base_type, array_level=prev.node_type.array_level + 1)


class ArrCallNode(ExprNode):
    def __init__(self, arr: IdentNode, *indexes: ExprNode,
                 column: Optional[int] = None, line: Optional[int] = None, **props):
        super().__init__(column=column, line=line, **props)
        self.arr = arr
        self.indexes = indexes

    @property
    def childs(self) -> Tuple[ExprNode, ...]:
        return self.indexes

    def __str__(self) -> str:
        return self.arr.__str__() + '[]' * len(self.indexes)

    def semantic_check(self, scope: IdentScope) -> None:
        self.arr.semantic_check(scope)
        count = 0
        for i in self.indexes:
            i.semantic_check(scope)
            count += 1
            if self.arr.node_type.array_level < count:
                self.semantic_error("Размерность массива " + self.arr.name + " = " + str(
                    self.arr.node_type.array_level) + ", а обращение идёт к элементу вложенности уровня " + str(count))
            if i.node_type.base_type != BaseType.INT or not i.node_type.is_simple or i.node_type.is_array:
                self.semantic_error("Индекс массива не целое число")
        self.node_type = TypeDesc(base_type_=self.arr.node_type.base_type,
                                  array_level=self.arr.node_type.array_level - count)
