<template>
  <div class="app-container">
    <!-- Header con Logo -->
    <header class="app-header">
      <div class="logo-container">
        <img src="../assets/aireconcienciaB.png" alt="AireConCiencia" class="logo">
        <div class="title-section">
          <h1>AireConCiencia</h1>
          <p class="tagline">Respira, aprende y cuida tu entorno</p>
        </div>
      </div>
      <button class="refresh-btn" @click="fetchSensorData" :disabled="loading">
        <span class="btn-icon">🔄</span>
        {{ loading ? 'Actualizando...' : 'Actualizar Datos' }}
      </button>
    </header>

    <!-- Contenido Principal -->
    <main class="main-content">
      <!-- Sección Superior: Ubicación y Estado Principal -->
      <div class="top-section">
        <div class="location-card card">
          <div class="card-header">
            <span class="card-icon">📍</span>
            <h3>Ubicación</h3>
          </div>
          <div class="card-content">
            <p class="location-name">Saltillo</p>
            <p class="sensor-info">Sensor: #31843</p>
          </div>
        </div>
        
        <div class="main-status-card card" :class="getStatusCardClass()">
          <div class="card-header">
            <h2>Calidad del Aire Actual</h2>
            <span class="update-time">{{ lastUpdate }}</span>
          </div>
          <div class="status-content">
            <!-- Sección de Imagen Visual -->
            <div class="visual-section">
              <img :src="getStatusImage()" :alt="getPmCategory()" class="status-image">
              <div class="image-caption">{{ getPmCategory() }}</div>
            </div>
            
            <div class="data-section">
              <div class="aqi-section">
                <div class="aqi-circle">
                  <span class="aqi-value">{{ formattedPmAvg }}</span>
                  <span class="aqi-label">PM Promedio</span>
                </div>
              </div>
              <div class="status-info">
                <div class="pm-values">
                  <div class="pm-item">
                    <span class="pm-label">PM1:</span>
                    <span class="pm-number">{{ sensorValues.pm1 || '--' }} µg/m³</span>
                  </div>
                  <div class="pm-item">
                    <span class="pm-label">PM2.5:</span>
                    <span class="pm-number">{{ sensorValues.pm25 || '--' }} µg/m³</span>
                  </div>
                  <div class="pm-item">
                    <span class="pm-label">PM10:</span>
                    <span class="pm-number">{{ sensorValues.pm10 || '--' }} µg/m³</span>
                  </div>
                </div>
                <p class="description">{{ getStatusDescription() }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="recommendation-card card">
          <div class="card-header">
            <span class="card-icon">💡</span>
            <h3>Recomendación Instantánea</h3>
          </div>
          <div class="card-content">
            <p class="recommendation-text">{{ getInstantRecommendation() }}</p>
          </div>
        </div>
      </div>

      <!-- Sección Inferior: Acciones y Más Información -->
      <div class="bottom-section">
        <div class="action-card card recomendaciones" @click="showRecommendations">
          <div class="card-icon">📋</div>
          <h3>Ver Recomendaciones</h3>
          <p>Guía completa según calidad del aire</p>
        </div>

        <div class="action-card card aprender" @click="showLearning">
          <div class="card-icon">📚</div>
          <h3>Aprender sobre el aire</h3>
          <p>Información educativa</p>
        </div>

        <div class="action-card card incidencia" @click="reportIncident">
          <div class="card-icon">⚠️</div>
          <h3>Reportar incidencia</h3>
          <p>Notificar problemas</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import Excelente from '../assets/Buena.png';
import Buena from '../assets/Moderada.png';
import Moderada from '../assets/Daninaparalasalud.png';
import PocoSaludable from '../assets/Daninaparagrupossensibles.png';
import Insalubre from '../assets/Peligrosa.png';
import Peligrosa from '../assets/Peligrosa.png';
import MuyDanina from '../assets/MuyDanina.png';

export default {
  name: 'AirQualityMonitor',
  data() {
    return {
      apiData: {},
      loading: false,
      error: null,
      lastUpdate: 'Haz clic en Actualizar Datos',
            statusImages: {
        'excelente': Excelente,
        'buena': Buena,
        'moderada': Moderada,
        'poco saludable': PocoSaludable,
        'insalubre': Insalubre,
        'peligrosa': Peligrosa,
        'cargando...': MuyDanina
      }
    }
  },
  computed: {
    // Datos combinados del AQI
    combinedData() {
      return this.apiData.combined || {};
    },
    // Valores de PM del sensor
    sensorValues() {
      return this.apiData.values || {};
    },
    // PM promedio formateado
    formattedPmAvg() {
      const pmAvg = this.sensorValues.pm_avg;
      return pmAvg ? pmAvg.toFixed(1) : '--';
    },
    // Subíndices individuales
    subindices() {
      return this.apiData.subindices || {};
    }
  },
  methods: {
    async fetchSensorData() {
      this.loading = true;
      this.error = null;
      
      try {
        const backendUrl = 'http://127.0.0.1:7777/api/aqi/combined';
        const response = await fetch(backendUrl);
        
        if (!response.ok) {
          throw new Error(`Error del servidor: ${response.status}`);
        }
        
        const data = await response.json();
        this.apiData = data;
        this.updateTime();
        
      } catch (err) {
        console.error('Error fetching sensor data:', err);
        this.error = `No se pudieron cargar los datos: ${err.message}`;
        alert(this.error);
      } finally {
        this.loading = false;
      }
    },

    updateTime() {
      const now = new Date();
      this.lastUpdate = `Actualizado: ${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
    },

    // Categorías basadas en PM promedio
    getPmCategory() {
      const pmAvg = this.sensorValues.pm_avg;
      if (!pmAvg) return 'Cargando...';
      
      if (pmAvg <= 12) return 'Excelente';
      if (pmAvg <= 35) return 'Buena';
      if (pmAvg <= 55) return 'Moderada';
      if (pmAvg <= 150) return 'Poco Saludable';
      if (pmAvg <= 250) return 'Insalubre';
      return 'Peligrosa';
    },

    // Obtener la imagen correspondiente al estado
    getStatusImage() {
      const category = this.getPmCategory().toLowerCase();
      return this.statusImages[category] || this.statusImages['cargando...'];
    },

    getStatusCardClass() {
      const pmAvg = this.sensorValues.pm_avg;
      if (!pmAvg) return 'status-unknown';
      
      if (pmAvg <= 12) return 'status-good';
      if (pmAvg <= 35) return 'status-moderate';
      if (pmAvg <= 55) return 'status-unhealthy-sensitive';
      if (pmAvg <= 150) return 'status-unhealthy';
      if (pmAvg <= 250) return 'status-very-unhealthy';
      return 'status-hazardous';
    },

    getStatusDescription() {
      const pmAvg = this.sensorValues.pm_avg;
      if (!pmAvg) return 'Haz clic en "Actualizar Datos" para obtener la información más reciente.';
      
      if (pmAvg <= 12) return 'La calidad del aire es ideal para actividades al aire libre.';
      if (pmAvg <= 35) return 'Calidad aceptable, ideal para la mayoría de actividades.';
      if (pmAvg <= 55) return 'Grupos sensibles deben considerar reducir actividades intensas al aire libre.';
      if (pmAvg <= 150) return 'Todas las personas pueden comenzar a experimentar efectos en la salud.';
      if (pmAvg <= 250) return 'Advertencia de condiciones sanitarias graves.';
      return 'Alerta de emergencia sanitaria. Evitar actividades al aire libre.';
    },

    getInstantRecommendation() {
      const pmAvg = this.sensorValues.pm_avg;
      if (!pmAvg) return 'Actualiza los datos para ver recomendaciones.';
      
      if (pmAvg <= 12) return 'Ideal para actividades al aire libre y deportes.';
      if (pmAvg <= 35) return 'Puedes realizar actividades normales al aire libre.';
      if (pmAvg <= 55) return 'Personas sensibles deben reducir actividades intensas al aire libre.';
      if (pmAvg <= 150) return 'Considera realizar actividades bajo techo.';
      if (pmAvg <= 250) return 'Realiza actividades bajo techo.';
      return 'Evita actividades al aire libre. Permanece en interiores.';
    },

    showRecommendations() {
      alert('Aquí se mostrarán las recomendaciones completas según la calidad del aire actual.');
    },

    showLearning() {
      alert('Sección educativa sobre calidad del aire.');
    },

    reportIncident() {
      alert('Formulario para reportar incidencias.');
    }
  }
}
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  padding: 20px;
}

/* Header Styles */
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 0 10px;
  flex-wrap: wrap;
  gap: 20px;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 1;
  min-width: 300px;
}

.logo {
  width: 150px;
  padding: 6px;
  height: auto;
  border-radius: 4px;
  background-color: white;
}

.title-section h1 {
  font-size: 2.2em;
  font-weight: 700;
  color: white;
  margin-bottom: 5px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.tagline {
  font-size: 1.1em;
  color: rgba(255, 255, 255, 0.95);
  font-weight: 400;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.refresh-btn {
  background: rgba(255, 255, 255, 0.25);
  border: 2px solid rgba(255, 255, 255, 0.4);
  color: white;
  padding: 14px 28px;
  border-radius: 25px;
  cursor: pointer;
  font-size: 1.1em;
  font-weight: 600;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  white-space: nowrap;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.35);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  font-size: 1.3em;
}

/* Main Content */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 10px;
}

/* Card Base Styles */
.card {
  background: white;
  border-radius: 20px;
  padding: 0;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.card-header {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 22px 28px;
  border-bottom: 2px solid #e9ecef;
  display: flex;
  align-items: center;
  gap: 15px;
}

.card-header h2,
.card-header h3 {
  color: #2c3e50;
  margin: 0;
  font-size: 1.4em;
  font-weight: 600;
}

.card-header h2 {
  font-size: 1.5em;
}

.card-content {
  padding: 28px;
}

.card-icon {
  font-size: 1.6em;
  width: 28px;
  text-align: center;
}

/* Top Section */
.top-section {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 25px;
  margin-bottom: 35px;
}

/* Location Card */
.location-card {
  display: flex;
  flex-direction: column;
  height: fit-content;
}

.location-name {
  font-size: 1.8em;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 10px;
}

.sensor-info {
  font-size: 1em;
  color: #6c757d;
  font-weight: 500;
}

/* Main Status Card - Layout Mejorado */
.main-status-card {
  min-height: 400px; /* Aumentado para acomodar la imagen */
}

.status-content {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 30px;
  padding: 30px 28px;
  align-items: center;
}

/* Sección de Imagen Visual */
.visual-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 15px;
}

.status-image {
  width: 100%;
  max-width: 280px;
  height: auto;
  border-radius: 15px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  object-fit: contain;
}

.image-caption {
  font-size: 1.4em;
  font-weight: 700;
  color: #2c3e50;
  text-align: center;
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Sección de Datos */
.data-section {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.aqi-section {
  display: flex;
  justify-content: center;
}

.aqi-circle {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
  border: 4px solid rgba(255, 255, 255, 0.8);
}

.aqi-value {
  font-size: 2.8em;
  line-height: 1;
  font-weight: 800;
}

.aqi-label {
  font-size: 1em;
  opacity: 0.95;
  margin-top: 5px;
  font-weight: 600;
  text-align: center;
}

.status-info {
  text-align: left;
}

.pm-values {
  margin-bottom: 20px;
  background: #f8f9fa;
  padding: 18px;
  border-radius: 12px;
  border-left: 4px solid #667eea;
}

.pm-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 6px 0;
}

.pm-item:last-child {
  margin-bottom: 0;
}

.pm-label {
  color: #495057;
  font-weight: 600;
  font-size: 1em;
}

.pm-number {
  color: #2c3e50;
  font-weight: 700;
  font-size: 1.1em;
  background: rgba(102, 126, 234, 0.1);
  padding: 4px 12px;
  border-radius: 8px;
}

.description {
  color: #495057;
  line-height: 1.6;
  font-size: 1.05em;
  font-weight: 500;
}

.update-time {
  font-size: 0.95em;
  color: #6c757d;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.7);
  padding: 4px 12px;
  border-radius: 12px;
}

/* Recommendation Card */
.recommendation-card {
  display: flex;
  flex-direction: column;
  height: fit-content;
}

.recommendation-text {
  color: #495057;
  line-height: 1.6;
  font-size: 1.05em;
  font-weight: 500;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  padding: 20px;
  border-radius: 12px;
  border-left: 4px solid #ffc107;
}

/* Status Card Colors */
.status-good .aqi-circle { background: linear-gradient(135deg, #4CAF50, #45a049); }
.status-moderate .aqi-circle { background: linear-gradient(135deg, #FFC107, #FF8F00); }
.status-unhealthy-sensitive .aqi-circle { background: linear-gradient(135deg, #FF9800, #F57C00); }
.status-unhealthy .aqi-circle { background: linear-gradient(135deg, #F44336, #D32F2F); }
.status-very-unhealthy .aqi-circle { background: linear-gradient(135deg, #9C27B0, #7B1FA2); }
.status-hazardous .aqi-circle { background: linear-gradient(135deg, #795548, #5D4037); }

/* Bottom Section */
.bottom-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 25px;
}


.action-card {
  text-align: center;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 20px;
  background-color: #e3f2fd;
}

.action-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 15px 45px rgba(0, 0, 0, 0.2);
}

.action-card .card-icon {
  font-size: 3em;
  margin-bottom: 18px;
  width: auto;
  transition: transform 0.3s ease;
}

.action-card:hover .card-icon {
  transform: scale(1.1);
}

.action-card h3 {
  color: #2c3e50;
  margin-bottom: 10px;
  font-size: 1.3em;
  font-weight: 600;
}

.action-card p {
  color: #6c757d;
  font-size: 0.95em;
  line-height: 1.5;
}

/* Responsive Design Mejorado */
@media (max-width: 1200px) {
  .top-section {
    grid-template-columns: 1fr 1.5fr 1fr;
    gap: 20px;
  }
  
  .status-content {
    grid-template-columns: 1fr 1.5fr;
    gap: 25px;
  }
}

@media (max-width: 1024px) {
  .top-section {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .bottom-section {
    grid-template-columns: repeat(2, 1fr);
  }

  .status-content {
    grid-template-columns: 1fr;
    text-align: center;
    gap: 25px;
    padding: 25px;
  }

  .visual-section {
    order: -1; /* La imagen va primero en móvil */
  }

  .status-info {
    text-align: center;
  }

  .pm-item {
    justify-content: space-around;
  }
}

@media (max-width: 768px) {
  .app-container {
    padding: 15px;
  }

  .app-header {
    flex-direction: column;
    gap: 20px;
    text-align: center;
    margin-bottom: 20px;
  }

  .logo-container {
    flex-direction: column;
    gap: 15px;
    min-width: auto;
  }

  .title-section h1 {
    font-size: 1.8em;
  }

  .refresh-btn {
    width: 100%;
    justify-content: center;
    padding: 16px 28px;
  }

  .bottom-section {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .top-section {
    gap: 20px;
  }

  .aqi-circle {
    width: 120px;
    height: 120px;
  }

  .aqi-value {
    font-size: 2.2em;
  }

  .status-image {
    max-width: 150px;
  }

  .image-caption {
    font-size: 1.2em;
  }

  .card-header {
    padding: 20px 25px;
  }

  .card-content {
    padding: 25px;
  }
}

@media (max-width: 480px) {
  .app-container {
    padding: 10px;
  }

  .status-content {
    padding: 20px 15px;
    gap: 20px;
  }

  .aqi-circle {
    width: 100px;
    height: 100px;
  }

  .aqi-value {
    font-size: 1.8em;
  }

  .status-image {
    max-width: 120px;
  }

  .image-caption {
    font-size: 1.1em;
  }

  .pm-values {
    padding: 15px;
  }

  .pm-item {
    flex-direction: column;
    gap: 5px;
    text-align: center;
  }
}
</style>