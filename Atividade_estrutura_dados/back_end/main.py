from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
from pydantic import BaseModel
import json, os

DB_FILE = "../dados.json"  # Simular banco de dados

class ItemFormula(BaseModel):
    name: str
    parent_name: Optional[str]
    qty: int
    unit_cost: float
    
def salvar_dados(itens):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(itens, f, indent=2)

def carregar_dados():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def build_tree(itens: List[Dict]) -> Optional[ItemFormula]:
    nodes = {it["name"]: ItemFormula(**it) for it in itens}
    for it in itens:
        parent = it["parent_name"]
        if parent and parent in nodes:
            nodes.setdefault(parent, nodes[parent])
            if not hasattr(nodes[parent], "children"):
                nodes[parent].children = []
            nodes[parent].children.append(nodes[it["name"]])
        nodes[it["name"]].children = getattr(nodes[it["name"]], "children", [])
    return next((n for n in nodes.values() if n.parent_name is None), None)

def calcular_total(node: ItemFormula) -> float:
    total = node.qty * node.unit_cost
    for c in getattr(node, "children", []):
        total += calcular_total(c)
    return total

def listar_componentes(node: ItemFormula, multiplicador=1):
    lista = {}
    def percorrer(n: ItemFormula, mult):
        qtd_final = n.qty * mult
        lista[n.name] = lista.get(n.name, 0) + qtd_final
        for c in getattr(n, "children", []):
            percorrer(c, qtd_final)
    percorrer(node, multiplicador)
    return lista

def serialize_tree(node: ItemFormula):
    return {
        "name": node.name,
        "qty": node.qty,
        "unit_cost": node.unit_cost,
        "total": calcular_total(node),
        "children": [serialize_tree(c) for c in getattr(node, "children", [])],
    }

app = FastAPI(title="API de Fórmulas")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# AQUI ESTÁ O ENDPOINTS PARA VOCE BATER
@app.get("/")
def home():
    return {"msg": "API de Fórmulas rodando"}

@app.post("/produtos/")
def cadastrar_produtos(itens: List[ItemFormula]):
    salvar_dados([i.dict() for i in itens])
    return {"msg": f"{len(itens)} itens cadastrados com sucesso"}

@app.get("/produtos/")
def listar_itens():
    return carregar_dados()

@app.get("/produtos/{nome}/explosao")
def explosao(nome: str):
    itens = carregar_dados()
    raiz = build_tree(itens)
    if not raiz or raiz.name != nome:
        raise HTTPException(404, "Produto não encontrado")
    return serialize_tree(raiz)

@app.get("/produtos/{nome}/implosao")
def implosao(nome: str, quantidade: int = 1):
    itens = carregar_dados()
    raiz = build_tree(itens)
    if not raiz or raiz.name != nome:
        raise HTTPException(404, "Produto não encontrado")
    return {
        "produto": nome,
        "quantidade": quantidade,
        "total": round(calcular_total(raiz) * quantidade, 2),
        "componentes": listar_componentes(raiz, quantidade),
    }

@app.put("/componentes/{nome}/preco")
def atualizar_preco(nome: str, novo_preco: float):
    itens = carregar_dados()
    found = False
    for item in itens:
        if item["name"].lower() == nome.lower():
            item["unit_cost"] = novo_preco
            found = True
    if not found:
        raise HTTPException(404, "Componente não encontrado")
    salvar_dados(itens)
    return {"msg": f"Preço de {nome} atualizado para {novo_preco:.2f}"}
