from typing import List, Union, Any

import visitor
from semantic import BaseType, TypeDesc, ScopeType, BinOp, SemanticException, BIN_OP_TYPE_COMPATIBILITY, \
    TYPE_CONVERTIBILITY
from mel_ast import AstNode, StmtNode, SingleIfNode, MultiIfNode, IdentNode, CallNode, WhenNode, WhenInnerNode, \
    WhileNode, ExprNode, LiteralNode, AssignNode, VarInitNode, VarTypeNode, BinOpNode, TypeConvertNode, \
    CommonFunDeclrNode, StmtListNode, ReturnNode, ForRangeNode

RUNTIME_CLASS_NAME = 'CompilerDemo.Runtime'
PROGRAM_CLASS_NAME = 'Program'


class CodeLabel:
    def __init__(self, prefix: str = 'L'):
        self.index = None
        self.prefix = prefix

    def __str__(self):
        return f'{self.prefix}_{self.index}'


class CodeLine:
    def __init__(self, code: Union[str, CodeLabel], *params: Union[str, CodeLabel], label: CodeLabel = None,
                 indent: str = None):
        if isinstance(code, CodeLabel):
            code, label = None, code
        self.code = code
        self.params = params
        self.label = label
        self.indent = indent

    def __str__(self):
        line = ''
        if self.label:
            if self.indent:
                line += self.indent[2:]
            line += f'{self.label}:'
            if self.code:
                line += ' '
        else:
            if self.indent:
                line += self.indent
        if self.code:
            line += self.code
            for p in self.params:
                line += ' ' + str(p)
        return line


class MsilException(Exception):
    """Класс для исключений во время генерации MSIL
       (на всякий случай, пока не используется)
    """

    def __init__(self, message, **kwargs: Any) -> None:
        self.message = message


MSIL_TYPE_NAMES = {
    BaseType.VOID: 'void',
    BaseType.INT: 'int32',
    BaseType.FLOAT: 'float32',
    BaseType.STR: 'string',
    BaseType.BOOL: 'int32'
}


def find_vars_decls(node: AstNode) -> List[StmtNode]:
    vars_nodes: List[StmtNode] = []

    def find(node_: AstNode) -> None:
        for n in (node_.childs or []):
            if isinstance(n, VarTypeNode) or isinstance(n, VarInitNode):
                vars_nodes.append(n)
            # if isinstance(n, IdentNode):
            #     vars_nodes.append(n)
            else:
                find(n)

    find(node)
    return vars_nodes


class CodeGenerator:
    def __init__(self):
        self.code_lines: List[CodeLine] = []

    def add(self, code: str, *params: Union[str, int, CodeLabel], label: CodeLabel = None):
        self.code_lines.append(CodeLine(code, *params, label=label))

    @property
    def code(self) -> [str, ...]:
        index = 0
        for cl in self.code_lines:
            line = cl.code
            if cl.label:
                cl.label.index = index
                index += 1
        code: List[str] = []
        for cl in self.code_lines:
            code.append(str(cl))
        return code

    def start(self) -> None:
        self.add('.assembly program')
        self.add('{')
        self.add('}')
        self.add('.class public Program')
        self.add('{')

    def end(self) -> None:
        self.add('}')

    @visitor.on('AstNode')
    def msil_gen(self, AstNode):
        """
        Нужен для работы модуля visitor (инициализации диспетчера)
        """
        pass

    @visitor.when(LiteralNode)
    def msil_gen(self, node: LiteralNode) -> None:
        if isinstance(node.value, int):
            self.add('    ldc.i4 {}'.format(node.value))
        elif isinstance(node.value, float):
            self.add('    ldc.r8 {}'.format(node.value))
        elif isinstance(node.value, str):
            self.add('    ldstr "{}"'.format(node.value))
        elif isinstance(node.value, bool):
            if node.value:
                self.add('    ldc.i4 1')
            else:
                self.add('    ldc.i4 0')
        else:
            pass

    @visitor.when(IdentNode)
    def msil_gen(self, node: IdentNode) -> None:
        if node.node_ident.scope == ScopeType.LOCAL:
            self.add('    ldloc', node.node_ident.index)
        elif node.node_ident.scope == ScopeType.PARAM:
            self.add('    ldarg', node.node_ident.index)
        elif node.node_ident.scope in (ScopeType.GLOBAL, ScopeType.GLOBAL_LOCAL):
            self.add(
                f'    ldsfld {MSIL_TYPE_NAMES[node.node_ident.type.base_type]} Program::_gv{node.node_ident.index}')

    @visitor.when(AssignNode)
    def msil_gen(self, node: AssignNode) -> None:
        node.val.msil_gen(self)
        var = node.var
        if var.node_ident.scope == ScopeType.LOCAL:
            self.add('    stloc', var.node_ident.index)
        elif var.node_ident.scope == ScopeType.PARAM:
            self.add('    starg', var.node_ident.index)
        elif var.node_ident.scope in (ScopeType.GLOBAL, ScopeType.GLOBAL_LOCAL):
            self.add(f'    stsfld {MSIL_TYPE_NAMES[var.node_ident.type.base_type]} Program::_gv{var.node_ident.index}')

    @visitor.when(VarInitNode)
    def msil_gen(self, node: VarInitNode) -> None:
        node.val.msil_gen(self)
        var = node.varType.var
        if var.node_ident.scope == ScopeType.LOCAL:
            self.add('    stloc', var.node_ident.index)
        elif var.node_ident.scope == ScopeType.PARAM:
            self.add('    starg', var.node_ident.index)
        elif var.node_ident.scope in (ScopeType.GLOBAL, ScopeType.GLOBAL_LOCAL):
            self.add(f'    stsfld {MSIL_TYPE_NAMES[var.node_ident.type.base_type]} Program::_gv{var.node_ident.index}')

    @visitor.when(BinOpNode)
    def msil_gen(self, node: BinOpNode) -> None:
        node.arg1.msil_gen(self)
        node.arg2.msil_gen(self)
        if node.op == BinOp.NEQUALS:
            if node.arg1.node_type == TypeDesc.STR:
                self.add('    call bool [mscorlib]System.String::op_Inequality(string, string)')
                self.add('    ldc.i4.0')
                self.add('    ceq')
            else:
                self.add('    ceq')
                self.add('    ldc.i4.0')
                self.add('    ceq')
        if node.op == BinOp.EQUALS:
            if node.arg1.node_type == TypeDesc.STR:
                self.add('    call bool [mscorlib]System.String::op_Inequality(string, string)')
            else:
                self.add('    ceq')
        elif node.op == BinOp.GT:
            self.add('    cgt')
            self.add('    ldc.i4.0')
            self.add('    ceq')
        elif node.op == BinOp.LT:
            self.add('    clt')
            self.add('    ldc.i4.0')
            self.add('    ceq')
        elif node.op == BinOp.LE:
            self.add('    cgt.un')
        elif node.op == BinOp.GE:
            self.add('    clt.un')
        elif node.op == BinOp.ADD:
            self.add('    add')
        elif node.op == BinOp.SUB:
            self.add('    sub')
        elif node.op == BinOp.MUL:
            self.add('    mul')
        elif node.op == BinOp.DIV:
            self.add('    div')
        else:
            pass

    @visitor.when(ReturnNode)
    def msil_gen(self, node: ReturnNode) -> None:
        node.val.msil_gen(self)
        self.add('    ret')

    @visitor.when(TypeConvertNode)
    def msil_gen(self, node: TypeConvertNode) -> None:
        node.expr.msil_gen(self)
        # часто встречаемые варианты будет реализовывать в коде, а не через класс Runtime
        if node.node_type.base_type == BaseType.FLOAT and node.expr.node_type.base_type == BaseType.INT:
            self.add('conv.r8')
        elif node.node_type.base_type == BaseType.BOOL and node.expr.node_type.base_type == BaseType.INT:
            self.add('ldc.i4.0')
            self.add('ceq')
            self.add('ldc.i4.0')
            self.add('ceq')
        else:
            cmd = f'call {MSIL_TYPE_NAMES[node.node_type.base_type]} class {RUNTIME_CLASS_NAME}::convert({MSIL_TYPE_NAMES[node.expr.node_type.base_type]}) '
            self.add(cmd)

    @visitor.when(CallNode)
    def msil_gen(self, node: CallNode) -> None:
        for param in node.params:
            self.msil_gen(param)
        class_name = RUNTIME_CLASS_NAME if node.func.node_ident.built_in else PROGRAM_CLASS_NAME
        param_types = ', '.join(MSIL_TYPE_NAMES[param.node_type.base_type] for param in node.params)
        cmd = f'call {MSIL_TYPE_NAMES[node.node_type.base_type]} class {class_name}::{node.func.name}({param_types})'
        self.add(cmd)

    @visitor.when(SingleIfNode)
    def msil_gen(self, node: SingleIfNode) -> None:
        node.cond.msil_gen(self)
        self.add('    ldc.i4', 0)
        self.add('    ceq')
        else_label = CodeLabel()
        end_label = CodeLabel()
        self.add('    brtrue', else_label)
        node.then_stmt.msil_gen(self)
        self.add('    br', end_label)
        self.add('', label=else_label)
        if node.else_stmt:
            node.else_stmt.msil_gen(self)
        self.add('', label=end_label)

    @visitor.when(ForRangeNode)
    def msil_gen(self, node: ForRangeNode) -> None:
        start_label = CodeLabel()
        end_label = CodeLabel()
        # node.param.msil_gen(self)
        self.add(f'  .locals init ( int32 _gv{node.param.node_ident.index})')
        node.start.msil_gen(self)
        self.add(f'  stloc.{node.param.node_ident.index}')
        self.add(start_label)
        self.add(f'   ldloc.{node.param.node_ident.index}')
        # node.start.msil_gen(self)
        node.end.msil_gen(self)
        self.add('   clt')
        self.add('   brfalse', end_label)
    #ldloc.0
# ldc.i4.1
# add
# stloc.0
        self.add(f'   ldloc.{node.param.node_ident.index}')
        self.add('   ldc.i4.1')
        self.add('   add')
        self.add(f'   stloc.{node.param.node_ident.index}')
        node.body.msil_gen(self)
        self.add('   br', start_label)
        self.add(end_label)

    @visitor.when(CommonFunDeclrNode)
    def msil_gen(self, node: CommonFunDeclrNode) -> None:
        params = ''
        for p in node.params:
            if len(params) > 0:
                params += ', '
            params += 'int32 ' + str(p.var.name)
        self.add('  .method public static void {}({}) cil managed'.format(node.name, params))
        self.add('  {')
        '''
        if 
        line = '.local init'

        .locals
        init([0]
        int32
        c,
        [1]
        int32
        CS$1$0000)
        '''
        node.body.msil_gen(self)
        self.add('  }')

    @visitor.when(StmtListNode)
    def msil_gen(self, node: StmtListNode) -> None:
        for stmt in node.exprs:
            stmt.msil_gen(self)

    def msil_gen_program(self, prog: StmtListNode):
        self.start()
        global_vars_decls = find_vars_decls(prog)
        for var in global_vars_decls:
            if isinstance(var, VarTypeNode):
                var = var.var
            elif isinstance(var, VarInitNode):
                var = var.varType.var
            if var.node_ident.scope in (ScopeType.GLOBAL, ScopeType.GLOBAL_LOCAL):
                self.add(f'  .field public static {MSIL_TYPE_NAMES[var.node_type.base_type]} _gv{var.node_ident.index}')
        for stmt in prog.exprs:
            if isinstance(stmt, CommonFunDeclrNode):
                self.msil_gen(stmt)
        self.add('')
        self.add('  .method public static void Main()')
        self.add('  {')
        self.add('    .entrypoint')
        for stmt in prog.childs:
            if not isinstance(stmt, CommonFunDeclrNode):
                self.msil_gen(stmt)

        self.add('ret')

        self.add('}')
        self.end()
