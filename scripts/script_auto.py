#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 18:03:29 2026

@author: airamsarmiento
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
script_auto.py
Descarga automáticamente datos de Copernicus (thetao y corrientes),
recorta la región de Canarias, genera la figura SST + Surface Currents
y guarda latest.png listo para la web.
"""
import os
import copernicusmarine
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.ticker import MaxNLocator
import xarray as xr
import pandas as pd
from datetime import datetime

today = datetime.utcnow().strftime("%Y-%m-%d")

# -----------------------------
# Login Copernicus
# -----------------------------
copernicusmarine.login(
    username=os.environ.get("COPERNICUS_USERNAME"),
    password=os.environ.get("COPERNICUS_PASSWORD")
)

#out_dir = "data/NC_copernicus"
#os.makedirs(out_dir, exist_ok=True)

# -----------------------------
#  1️⃣  Serie temporal zooplankton, mnkc, NPP
# -----------------------------
ds_bgc = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_glo_bgc_my_0.083deg-lmtl_P1D-i",
    variables=["zooc","npp","mnkc_epi"],
    minimum_longitude=-15.2976,
    maximum_longitude=-15.2976,
    minimum_latitude=28.1617,
    maximum_latitude=28.1617,
    start_datetime="2020-01-01",
    end_datetime=today
)
time = ds_bgc.time.values
zooc = ds_bgc["zooc"].isel(latitude=0, longitude=0).values
npp  = ds_bgc["npp"].isel(latitude=0, longitude=0).values
mnkc = ds_bgc["mnkc_epi"].isel(latitude=0, longitude=0).values
df = pd.DataFrame({
    "Date": pd.to_datetime(time),
    "Zooplankton (g/m²)": zooc,
    "Epipelagic micronekton (g/m²)": mnkc,
    "NPP (mg/m²/day)": npp
})

df.set_index("Date", inplace=True)

fig, axes = plt.subplots(3,1, figsize=(10,12), sharex=True)
axes[0].plot(df.index, df["Zooplankton (g/m²)"], marker='o'); axes[0].set_ylabel("Zooplankton [g/m²]"); axes[0].grid(True)
axes[1].plot(df.index, df["Epipelagic micronekton (g/m²)"], marker='o', color='orange'); axes[1].set_ylabel("Micronekton [g/m²]"); axes[1].grid(True)
axes[2].plot(df.index, df["NPP (mg/m²/day)"], marker='o', color='green'); axes[2].set_ylabel("NPP [mg/m²/day]"); axes[2].set_xlabel("Fecha"); axes[2].grid(True)
plt.tight_layout()

# -----------------------------
# Guardar figura
# -----------------------------

out_path = "figures"
os.makedirs(out_path, exist_ok=True)

SERIE_path = os.path.join(out_path, "series_temporal_point.png")
fig.savefig(SERIE_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Serie temporal guardada como series_temporal_point.png")




# -----------------------------
# 2️⃣ SST + Corrientes superficiales
# -----------------------------
ds_sst = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
    variables=["thetao"],
    minimum_longitude=-16.5,
    maximum_longitude=-13,
    minimum_latitude=26.2,
    maximum_latitude=29.5,
    start_datetime=today,
    end_datetime=today
)

ds_cur = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
    variables=["uo","vo"],
    minimum_longitude=-16.5,
    maximum_longitude=-13,
    minimum_latitude=26.2,
    maximum_latitude=29.5,
    start_datetime=today,
    end_datetime=today
)

sst = ds_sst["thetao"].isel(time=0, depth=0)
uo  = ds_cur["uo"].isel(time=0, depth=0)
vo  = ds_cur["vo"].isel(time=0, depth=0)
lons = ds_sst["longitude"].values
lats = ds_sst["latitude"].values
lon2d, lat2d = np.meshgrid(lons, lats)
date_str = str(np.datetime_as_string(ds_sst.time.values[0], unit='D'))

fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([-16.5, -13, 26.2, 29.5], crs=ccrs.PlateCarree())
pcm = ax.pcolormesh(lon2d, lat2d, sst.values, cmap='turbo', shading='auto', transform=ccrs.PlateCarree())
step = 4
q = ax.quiver(lon2d[::step,::step], lat2d[::step,::step],
              uo.values[::step,::step], vo.values[::step,::step],
              scale=1, scale_units='inches', width=0.0025, color='black',
              transform=ccrs.PlateCarree())
ax.quiverkey(q, 0.88, 0.04, 0.5, "0.5 m/s", labelpos='E', coordinates='axes', fontproperties={'size':10})
ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgrey')
ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.2)
gl = ax.gridlines(draw_labels=True, linewidth=0)
gl.top_labels = False
gl.right_labels = False
gl.left_labels = True
gl.bottom_labels = True

ax.set_title(f"SST + Surface Currents – {date_str}", fontsize=14)
cbar = plt.colorbar(pcm, orientation='vertical', pad=0.02, aspect=25)
cbar.set_label("Sea Surface Temperature (°C)", fontsize=12)
plt.tight_layout()


# -----------------------------
# Guardar figura
# -----------------------------


latest_path = os.path.join(out_path, "latest.png")
fig.savefig(latest_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como latest.png")


# -----------------------------
# 3️⃣ SST + flujo geostrófico
# -----------------------------
ds_SSH = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy-ssh_anfc_detided-0.027deg_P1D-m",
    variables=["zos_detided"],
    minimum_longitude=-16.5,
    maximum_longitude=-13,
    minimum_latitude=26.2,
    maximum_latitude=29.5,
    start_datetime=today,
    end_datetime=today
)
ssh = ds_SSH["zos_detided"].isel(time=0).values

# Calcular flujo geostrófico
lons = ds_SSH["longitude"].values
lats = ds_SSH["latitude"].values
lon2d, lat2d = np.meshgrid(lons, lats)
phi = np.deg2rad(lat2d)
f = 2*7.2921e-5*np.sin(phi)
dlat = np.deg2rad(lats[1]-lats[0])
dlon = np.deg2rad(lons[1]-lons[0])
dy = 6371000*dlat
dx = 6371000*np.cos(phi)*dlon
dssh_dy = np.gradient(ssh, axis=0)/dy
dssh_dx = np.gradient(ssh, axis=1)/dx
ugeo = -9.81/f*dssh_dy
vgeo = 9.81/f*dssh_dx

fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([-16.5,-13,26.2,29.5], crs=ccrs.PlateCarree())
pcm = ax.pcolormesh(lon2d, lat2d, ds_sst["thetao"].isel(time=0, depth=0).values,
                    cmap='turbo', shading='auto', transform=ccrs.PlateCarree())
step = 4
q = ax.quiver(lon2d[::step,::step], lat2d[::step,::step], ugeo[::step,::step], vgeo[::step,::step],
              scale=1, scale_units='inches', width=0.0025, color='black', transform=ccrs.PlateCarree())
ax.quiverkey(q, 0.88, 0.04, 0.5, "0.5 m/s", labelpos='E', coordinates='axes', fontproperties={'size':10})
ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgrey')
ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.2)
gl = ax.gridlines(draw_labels=True, linewidth=0)
gl.top_labels = False
gl.right_labels = False
gl.left_labels = True
gl.bottom_labels = True
plt.title(f"SST + Geostrophic Currents – {date_str}")
plt.colorbar(pcm, label="SST [°C]")
plt.tight_layout()


# -----------------------------
# Guardar figura
# -----------------------------

SSTgeo_path = os.path.join(out_path, "SSTgeo.png")
fig.savefig(SSTgeo_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como SSTgeo.png")




# -----------------------------
# 4️⃣ CHL + flujo geostrófico
# -----------------------------
ds_CHL = copernicusmarine.open_dataset(
    dataset_id="cmems_obs-oc_atl_bgc-plankton_my_l4-gapfree-multi-1km_P1D",
    variables=["CHL"],
    minimum_longitude=-16.5,
    maximum_longitude=-13,
    minimum_latitude=26.2,
    maximum_latitude=29.5,
    start_datetime="2026-02-16",
    end_datetime=today
)
time_chl = pd.to_datetime(ds_CHL.time.values)
last_date_chl = time_chl.max()
ds_CHL_day = ds_CHL.sel(time=last_date_chl)
lons_chl = ds_CHL_day["longitude"].values
lats_chl = ds_CHL_day["latitude"].values
lon2d_chl, lat2d_chl = np.meshgrid(lons_chl, lats_chl)

chl = ds_CHL_day["CHL"].values

## Crear figura
fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([lons_chl.min(), lons_chl.max(), lats_chl.min(), lats_chl.max()], crs=ccrs.PlateCarree())

# Colormesh de CHL usando paleta de SST ('turbo')
# Definir rango de colores según percentiles para no ser afectado por valores extremos
vmin = np.nanpercentile(chl, 5)    # valor por debajo del 5% se pone al mínimo color
vmax = np.nanpercentile(chl, 95)  # valor por encima del 95% se pone al máximo color

pcm = ax.pcolormesh(
    lon2d_chl, lat2d_chl, chl,
    cmap='jet', shading='auto',
    vmin=vmin, vmax=vmax,  # aquí ajustas la paleta
    transform=ccrs.PlateCarree()
)

# Interpolar flujo geostrófico a la malla de CHL
import xarray as xr

ugeo_da = xr.DataArray(ugeo, coords=[ds_sst.latitude, ds_sst.longitude], dims=["latitude", "longitude"])
vgeo_da = xr.DataArray(vgeo, coords=[ds_sst.latitude, ds_sst.longitude], dims=["latitude", "longitude"])

ugeo_interp = ugeo_da.interp(latitude=lats_chl, longitude=lons_chl)
vgeo_interp = vgeo_da.interp(latitude=lats_chl, longitude=lons_chl)

# Quiver
step = 10  # submuestreo para no saturar flechas
q = ax.quiver(
    lon2d_chl[::step, ::step],
    lat2d_chl[::step, ::step],
    ugeo_interp.values[::step, ::step],
    vgeo_interp.values[::step, ::step],
    scale=1, scale_units='inches', width=0.0025, color='black',
    transform=ccrs.PlateCarree()
)

ax.quiverkey(q, 0.88, 0.04, 0.5, "0.5 m/s", labelpos='E', coordinates='axes', fontproperties={'size':10})

# Añadir costa y tierra
ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgrey')
ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.2)

# Gridlines: solo izquierda y abajo
gl = ax.gridlines(draw_labels=True, linewidth=0)
gl.top_labels = False
gl.right_labels = False
gl.left_labels = True
gl.bottom_labels = True

# Título
ax.set_title(f"Chlorophyll + Geostrophic Currents – {last_date_chl.strftime('%Y-%m-%d')}")

# Colorbar
cbar = plt.colorbar(pcm, label="Chlorophyll [mg/m³]")

plt.tight_layout()



# -----------------------------
# Guardar figura
# -----------------------------

CHLgeo_path = os.path.join(out_path, "CHLgeo.png")
fig.savefig(CHLgeo_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como CHLgeo.png")




#### SSH

# -----------------------------
# SSH dataset
# -----------------------------
ds_SSH = copernicusmarine.open_dataset(
    dataset_id="cmems_mod_ibi_phy-ssh_anfc_detided-0.027deg_P1D-m",
    variables=["zos_detided"],
    minimum_longitude=-16.5,
    maximum_longitude=-13,
    minimum_latitude=26.2,
    maximum_latitude=29.5,
    start_datetime=today,
    end_datetime=today
)

ssh = ds_SSH["zos_detided"].isel(time=0).values
lons_ssh = ds_SSH["longitude"].values
lats_ssh = ds_SSH["latitude"].values
lon2d_ssh, lat2d_ssh = np.meshgrid(lons_ssh, lats_ssh)

# -----------------------------
# Reinterpolar flujo geostrófico si es necesario
# -----------------------------
# ugeo, vgeo vienen del SST o de tu cálculo geostrófico
ugeo_da = xr.DataArray(ugeo, coords=[ds_sst.latitude, ds_sst.longitude], dims=["latitude", "longitude"])
vgeo_da = xr.DataArray(vgeo, coords=[ds_sst.latitude, ds_sst.longitude], dims=["latitude", "longitude"])

ugeo_interp = ugeo_da.interp(latitude=lats_ssh, longitude=lons_ssh)
vgeo_interp = vgeo_da.interp(latitude=lats_ssh, longitude=lons_ssh)

# -----------------------------
# Crear figura
# -----------------------------
fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([lons_ssh.min(), lons_ssh.max(), lats_ssh.min(), lats_ssh.max()], crs=ccrs.PlateCarree())

# SSH
pcm = ax.pcolormesh(
    lon2d_ssh, lat2d_ssh, ssh,
    cmap='RdYlBu_r', shading='auto',
    transform=ccrs.PlateCarree()
)

# Flechas geostróficas
step = 4  # ajustar según densidad de flechas
q = ax.quiver(
    lon2d_ssh[::step, ::step], lat2d_ssh[::step, ::step],
    ugeo_interp.values[::step, ::step], vgeo_interp.values[::step, ::step],
    scale=1, scale_units='inches', width=0.0025,
    color='black', transform=ccrs.PlateCarree()
)

ax.quiverkey(q, 0.88, 0.04, 0.5, "0.5 m/s", labelpos='E', coordinates='axes', fontproperties={'size':10})

# Tierra y costa
ax.add_feature(cfeature.LAND.with_scale('10m'), facecolor='lightgrey')
ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1.2)

# Gridlines (solo etiquetas izquierda y abajo)
gl = ax.gridlines(draw_labels=True, linewidth=0)
gl.top_labels = False
gl.right_labels = False
gl.left_labels = True
gl.bottom_labels = True

# Título y colorbar
date_str = str(np.datetime_as_string(ds_SSH.time.values[0], unit='D'))
ax.set_title(f"SSH + Geostrophic Flow – {date_str}", fontsize=14)

cbar = plt.colorbar(pcm, orientation='vertical', pad=0.02, aspect=25)
cbar.set_label("Sea Surface Height [m]", fontsize=12)

plt.tight_layout()


# -----------------------------
# Guardar figura
# -----------------------------

SSHgeo_path = os.path.join(out_path, "SSHgeo.png")
fig.savefig(SSHgeo_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print("Figura guardada como SSHgeo.png")



