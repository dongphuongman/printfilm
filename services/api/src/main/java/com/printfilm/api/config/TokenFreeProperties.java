package com.printfilm.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "printfilm.tokenfree")
public record TokenFreeProperties(
        String baseUrl,
        String apiKey,
        String defaultModel,
        String defaultImageModel,
        String defaultImageEditModel,
        String defaultChatModel,
        /** TTS 模型，如 tts-1 / gpt-4o-mini-tts / step-tts-2；需在 TokenFree 控制台开通渠道 */
        String defaultTtsModel
) {
}
