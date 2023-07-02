import argparse

import program


def main() -> None:
    parser = argparse.ArgumentParser(description='Compiler demo program (msil)')
    parser.add_argument('src', type=str, help='source code file')
    parser.add_argument('--msil-only', default=False, action='store_true', help='print only msil code (no ast)')
    parser.add_argument('--jbc-only', default=False, action='store_true', help='print only java byte code (no ast)')
    args = parser.parse_args()

    with open(args.src, mode='r', encoding="utf-8") as f:
        src = f.read()

    program.execute(src, args.msil_only, args.jbc_only)



def main():
    prog1 = '''

    fun myFunc(i: Int, b: String): Int {
    println("e")
    return 1
    }

    fun pow(i: Int, b: Int): Float = b * i

    val i: Int = 10
    var b: Float = 11.2
    var c: String
    c = "str"
    when(i) {
    1 -> { i = 4}
    2 -> { i = 4}
    else -> {c = i - 10}
    }
    while (i>0) {
    when(i) {
    1 -> { i = 4}
    else -> {c = i - 10}
    }
    }
    var a: Int = 2
    if (a == b) {
    a = 10
    var e: Int = 1-4
    } else if (pow(10, a) > 0) {
    var t: String = readLine()
    } else {
    println("")
    }

    for (aaa in 5..7) {
    a = 10*12
    myFunc(a, c)
    }
    var arr: Array<Int> = Array(10)
    for (ip in arr) {
    var co: Boolean = true
    // var f: Float = ip
    var aa: Array<Array<Float>> = Array(30)
    var ar2: Array<Array<Float>> = arrayOf(arrayOf(0.1))
    }
    '''

    prog2 = '''//fun pow(i: Int, b: Int): Float = b * i

    for (o in 1..1000000000) {
    var k:Int = 1+1
    println(k)
    }
    '''
    program.execute(prog2)


if __name__ == "__main__":
    main()
