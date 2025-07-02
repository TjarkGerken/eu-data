/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  images: {
    unoptimized: true,
  },
  webpack: (config, { isServer }) => {
    config.ignoreWarnings = [
      {
        module: /node_modules\/@supabase\/realtime-js/,
        message:
          /Critical dependency: the request of a dependency is an expression/,
      },
    ];

    config.plugins.push({
      apply(compiler) {
        compiler.hooks.done.tap("LogBuildModulesPlugin", (stats) => {
          const info = stats.toJson();
          if (stats.hasErrors()) {
            console.error("\n\n🚨 Build Errors:");
            info.errors.forEach((e) => {
              console.error(e.message || e);
            });
          }
        });
      },
    });

    // Configure better-sqlite3 for server-side code
    if (isServer) {
      config.externals.push("better-sqlite3");
    }

    return config;
  },
};

export default nextConfig;
