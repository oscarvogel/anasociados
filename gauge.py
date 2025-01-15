import matplotlib.pyplot as plt
import numpy as np

# Función para generar un gráfico tipo gauge
def create_gauge(value, min_value=0, max_value=100, title="Gauge Example", output_file="gauge.png"):
    # Asegurarse de que el valor esté dentro del rango
    value = max(min_value, min(value, max_value))
    
    # Crear el gráfico
    theta = np.linspace(0, np.pi, 100)
    radii = [1] * len(theta)
    fig, ax = plt.subplots(figsize=(6, 3), subplot_kw={'projection': 'polar'})
    ax.set_theta_zero_location('N')  # Iniciar en el Norte
    ax.set_theta_direction(-1)       # Rotación en sentido horario
    ax.fill_between(theta, 0, radii, color="lightgray", alpha=0.5)
    
    # Calcular ángulo del valor
    angle = (value - min_value) / (max_value - min_value) * np.pi
    ax.plot([0, angle], [0, 1], color="red", linewidth=3)
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Añadir etiquetas
    ax.text(0, -0.3, f"{value}", fontsize=18, ha='center', va='center', transform=ax.transAxes)
    ax.text(0, -0.6, title, fontsize=14, ha='center', va='center', transform=ax.transAxes)
    
    # Guardar como imagen
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Cerrar el gráfico
    print(f"Gauge guardado como {output_file}")

if __name__ == "__main__":
    # Ejemplo de uso
    create_gauge(value=50, min_value=0, max_value=100, title="Gauge Example", output_file="gauge.png")