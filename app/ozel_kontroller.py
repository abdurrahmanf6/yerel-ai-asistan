import ast
import re

# Şifre/anahtar içerdiğini düşündüren değişken adları (Türkçe + İngilizce)
GIZLI_ISIM = re.compile(
    r"(sifre|şifre|parola|password|passwd|pwd|secret|token|api_?key)",
    re.IGNORECASE,
)


class OzelKontrol(ast.NodeVisitor):
    """Kod ağacını gezip kendi kurallarımıza uymayan yerleri işaretler."""

    def __init__(self):
        self.bulgular = []

    def ekle(self, node, kod, mesaj):
        self.bulgular.append({"satir": node.lineno, "kod": kod, "mesaj": mesaj})

    # Kural 1: sifre = "admin123" gibi gömülü gizli bilgiler
    def visit_Assign(self, node):
        deger = node.value
        if isinstance(deger, ast.Constant) and isinstance(deger.value, str) and deger.value:
            for hedef in node.targets:
                if isinstance(hedef, ast.Name) and GIZLI_ISIM.search(hedef.id):
                    self.ekle(node, "OZEL001",
                              f"Possible hardcoded secret in variable '{hedef.id}'")
        self.generic_visit(node)

    # Kural 2: x / len(liste) -> liste boşsa ZeroDivisionError
    def visit_BinOp(self, node):
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            payda = node.right
            if (isinstance(payda, ast.Call) and isinstance(payda.func, ast.Name)
                    and payda.func.id == "len"):
                self.ekle(node, "OZEL002",
                          "Division by len(...) raises ZeroDivisionError if the collection is empty")
        self.generic_visit(node)


def ozel_kontrolleri_calistir(kod):
    try:
        agac = ast.parse(kod)
    except SyntaxError as e:
        return [{"satir": e.lineno or 0, "kod": "SYNTAX", "mesaj": f"Syntax error: {e.msg}"}]
    kontrol = OzelKontrol()
    kontrol.visit(agac)
    return kontrol.bulgular