export const STORAGE_KEY = 'microservice-app-example-frontend'

let syncedData = {
  auth: {
    isLoggedIn: false,
    accessToken: null,
    refreshToken: null
  },
  user: {
    name: null
  }
}

// Sync with local storage.
if (localStorage.getItem(STORAGE_KEY)) {
  syncedData = JSON.parse(localStorage.getItem(STORAGE_KEY))
}
console.log('syncedData', syncedData)
// Merge data and export it.
export const state = Object.assign(syncedData)
