import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from task2_inciso1.KArmedBandit import (
    EstrategiaEpsilonGreedy,
    EstrategiaGreedy,
    EstrategiaUCB1,
    SimuladorBandit,
)


PASOS = 1000
EPISODIOS = 500
SEMILLA = 22809


def ejecutar(estacionario, estrategias, semilla=SEMILLA):
    simulador = SimuladorBandit(
        k=10,
        num_pasos=PASOS,
        num_episodios=EPISODIOS,
        estacionario=estacionario,
        intervalo_perturbacion=100,
        sigma_perturbacion=0.01,
        semilla=semilla,
    )
    return simulador.ejecutar(estrategias)


def primer_paso_separacion(ucb, epsilon, umbral=5.0, ventana=25):
    """Primer paso donde la ventaja de UCB supera el umbral toda una ventana."""
    diferencia = epsilon - ucb
    for inicio in range(len(diferencia) - ventana + 1):
        if np.all(diferencia[inicio:inicio + ventana] >= umbral):
            return inicio + 1
    return None


def main(mostrar_json=True):
    resultados = {}

    base = {
        "Greedy": lambda k: EstrategiaGreedy(k),
        "Epsilon-Greedy (epsilon=0.1)": lambda k: EstrategiaEpsilonGreedy(k, epsilon=0.1),
        "UCB1 (c=2)": lambda k: EstrategiaUCB1(k, c=2),
    }
    _, regret_est = ejecutar(True, base)
    resultados["estacionario_regret_final"] = {
        nombre: float(valores[-1]) for nombre, valores in regret_est.items()
    }
    resultados["paso_separacion_ucb_epsilon"] = primer_paso_separacion(
        regret_est["UCB1 (c=2)"], regret_est["Epsilon-Greedy (epsilon=0.1)"]
    )
    resultados["regret_estacionario_pasos"] = {
        str(paso): {
            nombre: float(valores[paso - 1]) for nombre, valores in regret_est.items()
        }
        for paso in (10, 25, 50, 100, 200, 500, 1000)
    }

    no_est = {
        "Greedy variable": lambda k: EstrategiaGreedy(k),
        "Greedy constante": lambda k: EstrategiaGreedy(k, alpha=0.05),
        "Epsilon 0.1 variable": lambda k: EstrategiaEpsilonGreedy(k, epsilon=0.1),
        "Epsilon 0.1 constante": lambda k: EstrategiaEpsilonGreedy(k, epsilon=0.1, alpha=0.05),
        "UCB c=2 variable": lambda k: EstrategiaUCB1(k, c=2),
        "UCB c=2 constante": lambda k: EstrategiaUCB1(k, c=2, alpha=0.05),
    }
    _, regret_no_est = ejecutar(False, no_est, SEMILLA + 1)
    resultados["no_estacionario_regret_final"] = {
        nombre: float(valores[-1]) for nombre, valores in regret_no_est.items()
    }

    epsilons = [0.01, 0.03, 0.05, 0.1, 0.2, 0.3]
    constantes_c = [0.25, 0.5, 1.0, 2.0, 4.0]
    sensibilidad = {
        **{f"epsilon={e}": (lambda k, e=e: EstrategiaEpsilonGreedy(k, epsilon=e)) for e in epsilons},
        **{f"c={c}": (lambda k, c=c: EstrategiaUCB1(k, c=c)) for c in constantes_c},
    }
    _, regret_sens_est = ejecutar(True, sensibilidad, SEMILLA + 2)
    resultados["sensibilidad_estacionaria"] = {
        nombre: float(valores[-1]) for nombre, valores in regret_sens_est.items()
    }

    sensibilidad_no_est = {
        **{f"epsilon={e}": (lambda k, e=e: EstrategiaEpsilonGreedy(k, epsilon=e, alpha=0.05)) for e in epsilons},
        **{f"c={c}": (lambda k, c=c: EstrategiaUCB1(k, c=c, alpha=0.05)) for c in constantes_c},
    }
    _, regret_sens_no_est = ejecutar(False, sensibilidad_no_est, SEMILLA + 3)
    resultados["sensibilidad_no_estacionaria_alpha_005"] = {
        nombre: float(valores[-1]) for nombre, valores in regret_sens_no_est.items()
    }

    figura, ejes = plt.subplots(1, 2, figsize=(12, 4.5))
    for eje, clave, titulo in (
        (ejes[0], "sensibilidad_estacionaria", "Entorno estacionario (paso variable)"),
        (ejes[1], "sensibilidad_no_estacionaria_alpha_005", "Entorno no estacionario (alpha=0.05)"),
    ):
        datos = resultados[clave]
        eje.plot(epsilons, [datos[f"epsilon={e}"] for e in epsilons], "o-", label="epsilon-greedy")
        eje.plot(constantes_c, [datos[f"c={c}"] for c in constantes_c], "s-", label="UCB1")
        eje.set_title(titulo)
        eje.set_xlabel("Hiperparámetro (epsilon o c)")
        eje.set_ylabel("Regret acumulado final")
        eje.grid(True, alpha=0.3)
        eje.legend()
    figura.tight_layout()
    figura.savefig("sensibilidad_hiperparametros.png", dpi=160)

    with open("resultados_inciso2.json", "w", encoding="utf-8") as archivo:
        json.dump(resultados, archivo, indent=2, ensure_ascii=False)

    if mostrar_json:
        print(json.dumps(resultados, indent=2, ensure_ascii=False))
    return resultados


if __name__ == "__main__":
    main()
