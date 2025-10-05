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
  background-color: #64b5f6;
}

#app {
  min-height: 100vh;
}
</style>