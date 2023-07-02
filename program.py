import os
import sys
import traceback

import mel_parser as parser
import msil
import semantic


# def execute1(prog: str) -> None:
#     prog = parser.parse(prog)
#
#     print('ast:')
#     print(*prog.tree, sep=os.linesep)
#     print()
#
#     print('semantic_check:')
#     try:
#         scope = semantic.prepare_global_scope()
#         prog.semantic_check(scope)
#         print(*prog.tree, sep=os.linesep)
#     except semantic.SemanticException as e:
#         print('Ошибка: {}'.format(e.message))
#         return
#     print()
#
#     print('msil:')
#     try:
#         gen = msil.CodeGenerator()
#         gen.msil_gen_program(prog)
#         print(*gen.code, sep=os.linesep)
#     except msil.MsilException as e:
#         print('Ошибка: {}'.format(e.message))
#         return
#     print()


def execute(prog: str, msil_only: bool = False, jbc_only: bool = False) -> None:
    try:
        prog = parser.parse(prog)
    except Exception as e:
        print('Ошибка: {}'.format(e.__cause__), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        exit(1)

    if not (msil_only or jbc_only):
        print('ast:')
        print(*prog.tree, sep=os.linesep)

    # print('semantic_check:')
    try:
        scope = semantic.prepare_global_scope()
        prog.semantic_check(scope)
        # print(*prog.tree, sep=os.linesep)
    except semantic.SemanticException as e:
        print('Ошибка: {}'.format(e.message), file=sys.stderr)
        exit(2)

    # print('msil:')
    try:
        gen = msil.CodeGenerator()
        gen.msil_gen_program(prog)
        print(*gen.code, sep=os.linesep)
    except msil.MsilException or Exception as e:
        print('Ошибка: {}'.format(e.message), file=sys.stderr)
        exit(3)
    print()

    # if not (msil_only or jbc_only):
    #     print()
    #     print('msil:')
    # if not jbc_only:
    #     try:
    #         gen = msil.MsilCodeGenerator()
    #         gen.gen_program(prog)
    #         print(*gen.code, sep=os.linesep)
    #     except msil.MsilException or Exception as e:
    #         print('Ошибка: {}'.format(e.message), file=sys.stderr)
    #         exit(3)
    #
    # if not (msil_only or jbc_only):
    #     print()
    #     print('jbc:')
    # if not msil_only:
    #     try:
    #         gen = jbc.JbcCodeGenerator(file_name)
    #         gen.gen_program(prog)
    #         print(*gen.code, sep=os.linesep)
    #     except jbc.JbcException or Exception as e:
    #         print('Ошибка: {}'.format(e.message), file=sys.stderr)
    #         exit(4)
