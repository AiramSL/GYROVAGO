# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import os

# Crear carpeta figures si no existe
os.makedirs("../figures", exist_ok=True)

# Leer CSV de ejemplo
data = pd.read_csv("../data/biomass.csv")

# Convertir fechas
data['date'] = pd.to_datetime(data['date'])

# Crear gráfico de biomasa
plt.figure(figsize=(8,5))
plt.plot(data['date'], data['biomass'], marker='o', linestyle='-')
plt.xticks(rotation=45)
plt.ylabel("Biomass (tons)")
plt.title("Daily Mesopelagic Biomass")
plt.tight_layout()

# Guardar gráfico
plt.savefig("../figures/biomass_plot.png")
plt.close()