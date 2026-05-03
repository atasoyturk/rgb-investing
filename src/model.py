from keras.models import Model
from keras.layers import (
    Conv2D, MaxPooling2D, Dense, Dropout,
    BatchNormalization, GlobalAveragePooling2D,
    Reshape, Multiply, Input, TimeDistributed,
)
from config import DROPOUT_RATE


def se_block(x, ratio: int = 8):
    channels = x.shape[-1]
    se = GlobalAveragePooling2D()(x)
    se = Dense(channels // ratio, activation="relu")(se)
    se = Dense(channels, activation="sigmoid")(se)
    se = Reshape((1, 1, channels))(se)
    return Multiply()([x, se])


def build_model(image_size: int = 20, n_features: int = 10) -> Model:
    
    inputs = Input(shape=(image_size, image_size, n_features))

    # Learned linear mixing: n_features → 3, no bias, same weights everywhere
    projected = TimeDistributed(
        TimeDistributed(Dense(3, use_bias=False))
    )(inputs)

    # Block 1: standard conv
    x = Conv2D(32, (3, 3), activation="relu", padding="same", dilation_rate=(1, 1))(projected)
    x = BatchNormalization()(x)
    x = se_block(x, ratio=4)

    # Block 2: dilated conv — short-term vertical pattern
    x = Conv2D(64, (3, 3), activation="relu", padding="same", dilation_rate=(2, 1))(x)
    x = BatchNormalization()(x)
    x = se_block(x, ratio=8)

    if image_size == 20:
        x = MaxPooling2D((2, 2))(x)

    # Block 3: dilated conv — medium-term vertical pattern
    x = Conv2D(64, (3, 3), activation="relu", padding="same", dilation_rate=(4, 1))(x)
    x = BatchNormalization()(x)
    x = se_block(x, ratio=8)

    x = MaxPooling2D((2, 2))(x)
    x = GlobalAveragePooling2D()(x)
    x = Dropout(DROPOUT_RATE)(x)
    outputs = Dense(1, activation="sigmoid")(x)

    model = Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model
