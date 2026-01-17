module.exports = {
  environment: process.env.NODE_ENV || 'development',
  isDev: process.env.NODE_ENV === 'dev',
  isProduction: process.env.NODE_ENV === 'production'
};