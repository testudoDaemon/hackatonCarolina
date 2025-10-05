<template>
  <div id="app">
    <AirQualityMonitor />
  </div>
</template>

<script>
import AirQualityMonitor from './components/AirQualityMonitor.vue'

export default {
  name: 'App',
  components: {
    AirQualityMonitor
  }
}
</script>


<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  min-height: 100vh;
background: linear-gradient(100deg, #b5e2fa 0%, #f9f7f3 100%);}

#app {
  min-height: 100vh;
}
</style>