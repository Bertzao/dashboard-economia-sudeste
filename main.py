# -*- coding: utf-8 -*-
"""
============================================================================
MAIN — ORQUESTRADOR PRINCIPAL DO PROJETO
Economia Regional e Urbana — Região Sudeste do Brasil
============================================================================
Executa todos os módulos em sequência ou individualmente.
"""

import sys
import time

import config as cfg
import utils
from modulo1_estrutura_admin import executar_modulo1
from modulo2_populacao import executar_modulo2
from modulo3_infraestrutura import executar_modulo3
from modulo4_economia import executar_modulo4
from modulo4_1_emprego import executar_modulo4_1
from modulo5_historico_colonial import executar_modulo5


def menu():
    """Exibe menu interativo para seleção de módulos."""
    print("\n" + "=" * 60)
    print("  PROJETO: ECONOMIA REGIONAL E URBANA")
    print("  Análise da Região Sudeste do Brasil")
    print("  Modelos: Von Thünen | Weber | Christaller | Lösch")
    print("=" * 60)
    print("  [1] Módulo 1 — Estrutura Político-Administrativa")
    print("  [2] Módulo 2 — Estrutura Populacional")
    print("  [3] Módulo 3 — Infraestrutura e Meio Ambiente")
    print("  [4] Módulo 4 — Atividade Econômica e Modelos Clássicos")
    print("  [41] Módulo 4.1 — QL por Empregos (CEMPRE)")
    print("  [5] Módulo 5 — Histórico Colonial e Limites Territoriais")
    print("  [6] Executar TODOS os módulos")
    print("  [0] Sair\n")


def main():
    # Verificar caminhos
    print("Verificando arquivos de dados...")
    missing = []
    for name, path in [("Shapefile Municípios", cfg.SHP_MUNICIPIOS),
                        ("Pop. Idade", cfg.XLS_POP_IDADE),
                        ("PAM", cfg.XLS_PAM)]:
        import os
        if not os.path.exists(path):
            missing.append(name)
    if missing:
        print(f"⚠ Arquivos não encontrados: {', '.join(missing)}")

    while True:
        menu()
        try:
            escolha = input("  Escolha uma opção: ").strip()
        except (EOFError, KeyboardInterrupt):
            escolha = "0"

        t0 = time.time()

        try:
            if escolha == "1":
                executar_modulo1()
            elif escolha == "2":
                gdf = utils.carregar_municipios_sudeste()
                executar_modulo2(gdf)
            elif escolha == "3":
                gdf = utils.carregar_municipios_sudeste()
                executar_modulo3(gdf)
            elif escolha == "4":
                gdf = utils.carregar_municipios_sudeste()
                gdf["CD_MUN"] = gdf["CD_MUN"].astype(str)
                executar_modulo4(gdf)
            elif escolha == "41":
                gdf = utils.carregar_municipios_sudeste()
                gdf["CD_MUN"] = gdf["CD_MUN"].astype(str)
                executar_modulo4_1(gdf)
            elif escolha == "5":
                executar_modulo5()
            elif escolha == "6":
                gdf = executar_modulo1()
                executar_modulo2(gdf)
                executar_modulo3(gdf)
                gdf["CD_MUN"] = gdf["CD_MUN"].astype(str)
                executar_modulo4(gdf)
                executar_modulo4_1(gdf)
                executar_modulo5()
            elif escolha == "0":
                print("\nAté logo!")
                break
            else:
                print("\n⚠ Opção inválida.")
                continue

            elapsed = time.time() - t0
            print(f"\n⏱ Tempo de execução: {elapsed:.1f} segundos")

        except Exception as e:
            print(f"\n✗ Erro na execução: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        gdf = executar_modulo1()
        executar_modulo2(gdf)
        executar_modulo3(gdf)
        gdf["CD_MUN"] = gdf["CD_MUN"].astype(str)
        executar_modulo4(gdf)
        executar_modulo5()
    else:
        main()
