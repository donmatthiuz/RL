import numpy as np
import matplotlib.pyplot as plt


class KArmedBandit:
    def __init__(self, k=10, estacionario=True, intervalo_perturbacion=100, sigma_perturbacion=0.01, sigma_recompensa=1.0):
        self.k = k
        self.estacionario = estacionario
        self.intervalo_perturbacion = intervalo_perturbacion
        self.sigma_perturbacion = sigma_perturbacion
        self.sigma_recompensa = sigma_recompensa
        self.reiniciar()

    def reiniciar(self):
        if self.estacionario:
            self.valores_reales = np.random.normal(0, 1, self.k)
        else:
            self.valores_reales = np.zeros(self.k)
        self.paso_actual = 0

    def obtener_recompensa(self, accion):
        recompensa = np.random.normal(self.valores_reales[accion], self.sigma_recompensa)
        self.paso_actual += 1
        if not self.estacionario and self.paso_actual % self.intervalo_perturbacion == 0:
            self._perturbar()
        return recompensa

    def _perturbar(self):
        self.valores_reales += np.random.normal(0, self.sigma_perturbacion, self.k)

    def accion_optima(self):
        return int(np.argmax(self.valores_reales))

    def mejor_valor(self):
        return np.max(self.valores_reales)


class EstrategiaBase:
    def __init__(self, k, alpha=None):
        self.k = k
        self.alpha = alpha
        self.reiniciar()

    def reiniciar(self):
        self.valores_estimados = np.zeros(self.k)
        self.conteo_acciones = np.zeros(self.k)
        self.paso_actual = 0

    def select_action(self):
        raise NotImplementedError

    def update(self, accion, recompensa):
        self.paso_actual += 1
        self.conteo_acciones[accion] += 1
        if self.alpha is None:
            paso = 1 / self.conteo_acciones[accion]
        else:
            paso = self.alpha
        self.valores_estimados[accion] += paso * (recompensa - self.valores_estimados[accion])


class EstrategiaGreedy(EstrategiaBase):
    def select_action(self):
        return int(np.argmax(self.valores_estimados))


class EstrategiaEpsilonGreedy(EstrategiaBase):
    def __init__(self, k, epsilon=0.1, alpha=None):
        self.epsilon = epsilon
        super().__init__(k, alpha)

    def select_action(self):
        if np.random.random() < self.epsilon:
            return np.random.randint(self.k)
        return int(np.argmax(self.valores_estimados))


class EstrategiaUCB1(EstrategiaBase):
    def __init__(self, k, c=2, alpha=None):
        self.c = c
        super().__init__(k, alpha)

    def select_action(self):
        for accion in range(self.k):
            if self.conteo_acciones[accion] == 0:
                return accion
        valores_ucb = self.valores_estimados + self.c * np.sqrt(np.log(self.paso_actual) / self.conteo_acciones)
        return int(np.argmax(valores_ucb))


class SimuladorBandit:
    def __init__(self, k=10, num_pasos=1000, num_episodios=500, estacionario=True, intervalo_perturbacion=100, sigma_perturbacion=0.01):
        self.k = k
        self.num_pasos = num_pasos
        self.num_episodios = num_episodios
        self.estacionario = estacionario
        self.intervalo_perturbacion = intervalo_perturbacion
        self.sigma_perturbacion = sigma_perturbacion

    def ejecutar(self, estrategias):
        recompensa_promedio = {nombre: np.zeros(self.num_pasos) for nombre in estrategias}
        regret_acumulado = {nombre: np.zeros(self.num_pasos) for nombre in estrategias}

        for _ in range(self.num_episodios):
            entorno = KArmedBandit(
                k=self.k,
                estacionario=self.estacionario,
                intervalo_perturbacion=self.intervalo_perturbacion,
                sigma_perturbacion=self.sigma_perturbacion,
            )
            valores_reales_iniciales = entorno.valores_reales.copy()

            for nombre, fabrica_estrategia in estrategias.items():
                entorno.valores_reales = valores_reales_iniciales.copy()
                entorno.paso_actual = 0
                estrategia = fabrica_estrategia(self.k)
                regret_episodio = 0.0

                for paso in range(self.num_pasos):
                    accion = estrategia.select_action()
                    mejor_valor = entorno.mejor_valor()
                    recompensa = entorno.obtener_recompensa(accion)
                    estrategia.update(accion, recompensa)

                    recompensa_promedio[nombre][paso] += recompensa
                    regret_episodio += mejor_valor - recompensa
                    regret_acumulado[nombre][paso] += regret_episodio

        for nombre in estrategias:
            recompensa_promedio[nombre] /= self.num_episodios
            regret_acumulado[nombre] /= self.num_episodios

        return recompensa_promedio, regret_acumulado

    def graficar(self, recompensa_promedio, regret_acumulado, titulo, sufijo_archivo):
        figura, (eje1, eje2) = plt.subplots(1, 2, figsize=(14, 5))

        for nombre, valores in recompensa_promedio.items():
            eje1.plot(valores, label=nombre)
        eje1.set_title(f"Recompensa promedio - {titulo}")
        eje1.set_xlabel("Pasos")
        eje1.set_ylabel("Recompensa promedio")
        eje1.legend()
        eje1.grid(True)

        for nombre, valores in regret_acumulado.items():
            eje2.plot(valores, label=nombre)
        eje2.set_title(f"Regret acumulado - {titulo}")
        eje2.set_xlabel("Pasos")
        eje2.set_ylabel("Regret acumulado")
        eje2.legend()
        eje2.grid(True)

        plt.tight_layout()
        plt.show()
