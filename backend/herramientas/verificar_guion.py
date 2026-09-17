"""Corre un guion a reloj acelerado y muestra la línea de tiempo de alertas.

    python -m herramientas.verificar_guion exfiltracion-iot

Sirve para comprobar que la demo es determinística y que la alerta crítica
correlacionada cae donde tiene que caer.
"""

from __future__ import annotations

import sys
from trace.almacen import Almacen
from trace.motor import Motor

LIMITE_S = 180.0


def main() -> int:
    guion_id = sys.argv[1] if len(sys.argv) > 1 else "exfiltracion-iot"
    limite = float(sys.argv[2]) if len(sys.argv) > 2 else LIMITE_S
    motor = Motor(almacen=Almacen("sqlite://"))
    motor.preparar(guion_id)

    criticas: list[float] = []
    while True:
        t, alertas, terminado = motor.paso()
        for alerta in alertas:
            print(f"t={t:6.2f}s  {alerta.severidad:8s} {alerta.regla:24s} "
                  f"{alerta.dispositivo_id:8s} {alerta.titulo}")
            if alerta.severidad == "critica":
                criticas.append(t)
        if terminado or t >= limite:
            break

    metricas = motor.metricas(t)
    print(f"\nHasta t={t:.0f}s: {motor._alertas_generadas} alertas, "
          f"{metricas.flujos_activos} flujos activos, "
          f"{metricas.porcentaje_cifrado} % cifrado, "
          f"{metricas.mbps_subida} Mbps de subida.")
    if criticas:
        print(f"Primera alerta crítica a los {criticas[0]:.2f} s.")
    else:
        print("Sin alertas críticas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
