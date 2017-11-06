#!/usr/bin/env python
# encoding=utf-8
# Created by andy on 2016-07-31 16:57.
import common

__author__ = "andy"
import tensorflow as tf


# Utility functions
def weight_variable(shape, name=None):
    initial = tf.truncated_normal(shape, stddev=0.5)
    return tf.Variable(initial, name=name)


def bias_variable(shape, name=None):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial, name=name)


def conv2d(x, W, stride=(1, 1), padding='SAME'):
    return tf.nn.conv2d(x, W, strides=[1, stride[0], stride[1], 1],
                        padding=padding)


def max_pool(x, ksize=(2, 2), stride=(2, 2)):
    return tf.nn.max_pool(x, ksize=[1, ksize[0], ksize[1], 1],
                          strides=[1, stride[0], stride[1], 1], padding='SAME')


def avg_pool(x, ksize=(2, 2), stride=(2, 2)):
    return tf.nn.avg_pool(x, ksize=[1, ksize[0], ksize[1], 1],
                          strides=[1, stride[0], stride[1], 1], padding='SAME')


def convolutional_layers():
    """
    Get the convolutional layers of the model.
    """
    with tf.name_scope('inputs'):
        inputs = tf.placeholder(tf.float32, [None, None, common.OUTPUT_SHAPE[0]], name='inputs')
    with tf.name_scope('input_expand_dims'):
        x_expanded = tf.expand_dims(inputs, 3)
    with tf.name_scope('input_reshape'):
        image_shaped_input = tf.reshape(x_expanded, [-1, common.OUTPUT_SHAPE[0], common.OUTPUT_SHAPE[1], 1])
        tf.summary.image('input', image_shaped_input, common.BATCH_SIZE)  # 一次显示BATCH_SIZE个图像，即输入样本的个数
    with tf.name_scope(''):
        # Batch Normalization（批标准化）
        axes = list(range(len(x_expanded.get_shape()) - 1))
        fc_mean, fc_var = tf.nn.moments(
            x_expanded,
            axes=axes
            # 想要 normalize 的维度, [0] 代表 batch 维度 # 如果是图像数据, 可以传入 [0, 1, 2], 相当于求[batch, height, width] 的均值/方差, 注意不要加入 channel 维度
        )
        scale = tf.Variable(tf.ones(fc_mean.get_shape()))
        shift = tf.Variable(tf.zeros(fc_mean.get_shape()))
        epsilon = 0.001
        x_expanded = tf.nn.batch_normalization(x_expanded, fc_mean, fc_var, shift, scale, epsilon)
    with tf.name_scope('conv'):
        # First layer
        with tf.name_scope('layer1'):
            layer_name = 'layer1'
            with tf.name_scope('weights'):
                W_conv1 = weight_variable([5, 5, 1, 48], name='W')
                tf.summary.histogram(layer_name + '/weights', W_conv1)
            with tf.name_scope('biases'):
                b_conv1 = bias_variable([48], name='b')
                tf.summary.histogram(layer_name + '/biases', b_conv1)
            h_conv1 = tf.nn.relu(conv2d(x_expanded, W_conv1) + b_conv1)
            h_pool1 = max_pool(h_conv1, ksize=(2, 2), stride=(2, 2))
            tf.summary.histogram(layer_name + '/outputs', h_pool1)

        # Second layer
        with tf.name_scope('layer2'):
            layer_name = 'layer2'
            with tf.name_scope('weights'):
                W_conv2 = weight_variable([5, 5, 48, 64], name='W')
                tf.summary.histogram(layer_name + '/weights', W_conv2)
            with tf.name_scope('biases'):
                b_conv2 = bias_variable([64], name='b')
                tf.summary.histogram(layer_name + '/biases', b_conv2)

            h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2) + b_conv2)
            h_pool2 = max_pool(h_conv2, ksize=(2, 1), stride=(2, 1))
            tf.summary.histogram(layer_name + '/outputs', h_pool2)

        # Third layer
        with tf.name_scope('layer3'):
            layer_name = 'layer3'
            with tf.name_scope('weights'):
                W_conv3 = weight_variable([5, 5, 64, 128], name='W')
                tf.summary.histogram(layer_name + '/weights', W_conv3)
            with tf.name_scope('biases'):
                b_conv3 = bias_variable([128], name='b')
                tf.summary.histogram(layer_name + '/biases', b_conv3)
            h_conv3 = tf.nn.relu(conv2d(h_pool2, W_conv3) + b_conv3)
            h_pool3 = max_pool(h_conv3, ksize=(2, 2), stride=(2, 2))
            tf.summary.histogram(layer_name + '/outputs', h_pool3)

        # Densely connected layer
        with tf.name_scope('fc-layer'):
            layer_name = 'fc-layer'
            with tf.name_scope('weights'):
                W_fc1 = weight_variable([32 * 8 * common.OUTPUT_SHAPE[1], common.OUTPUT_SHAPE[1]], name='W')
                tf.summary.histogram(layer_name + '/weights', W_fc1)
            with tf.name_scope('biases'):
                b_fc1 = bias_variable([common.OUTPUT_SHAPE[1]], name='b')
                tf.summary.histogram(layer_name + '/biases', b_fc1)
            conv_layer_flat = tf.reshape(h_pool3, [-1, 32 * 8 * common.OUTPUT_SHAPE[1]])
            features = tf.nn.relu(tf.matmul(conv_layer_flat, W_fc1) + b_fc1)
            tf.summary.histogram(layer_name + '/outputs', features)
    shape = tf.shape(features)
    features = tf.reshape(features, [shape[0], common.OUTPUT_SHAPE[1], 1])  # batchsize * outputshape * 1
    return inputs, features


def lstm_cell(is_training=True):
    lstm_cell = tf.contrib.rnn.LSTMCell(common.num_hidden)
    # 在外面包裹一层dropout
    if is_training and common.KEEP_PROB < 1:
        lstm_cell = tf.nn.rnn_cell.DropoutWrapper(
            lstm_cell, output_keep_prob=common.KEEP_PROB)
    return lstm_cell


def get_train_model(is_training=True):
    # Has size [batch_size, max_stepsize, num_features], but the
    # batch_size and max_stepsize can vary along each step
    inputs, features = convolutional_layers()

    if is_training and common.KEEP_PROB < 1:
        # 在外面包裹一层dropout
        features = tf.nn.dropout(features, common.KEEP_PROB)
    # print features.get_shape()

    # inputs = tf.placeholder(tf.float32, [None, None, common.OUTPUT_SHAPE[0]])

    # Here we use sparse_placeholder that will generate a
    # SparseTensor required by ctc_loss op.
    targets = tf.sparse_placeholder(tf.int32)

    # 1d array of size [batch_size]
    seq_len = tf.placeholder(tf.int32, [None])

    # Defining the cell
    # Can be:
    #   tf.nn.rnn_cell.RNNCell
    #   tf.nn.rnn_cell.GRUCell
    # cell = tf.contrib.rnn.LSTMCell(common.num_hidden, state_is_tuple=True)

    # Stacking rnn cells
    stack = tf.contrib.rnn.MultiRNNCell([lstm_cell(is_training) for _ in range(0, common.num_layers)],
                                        state_is_tuple=True)

    # The second output is the last state and we will no use that
    outputs, _ = tf.nn.dynamic_rnn(stack, features, seq_len, dtype=tf.float32)

    shape = tf.shape(features)
    batch_s, max_timesteps = shape[0], shape[1]

    # Reshaping to apply the same weights over the timesteps
    outputs = tf.reshape(outputs, [-1, common.num_hidden])

    # Truncated normal with mean 0 and stdev=0.1
    # Tip: Try another initialization
    # see https://www.tensorflow.org/versions/r0.9/api_docs/python/contrib.layers.html#initializers
    W = tf.Variable(tf.truncated_normal([common.num_hidden,
                                         common.num_classes],
                                        stddev=0.1), name="W")
    # Zero initialization
    # Tip: Is tf.zeros_initializer the same?
    b = tf.Variable(tf.constant(0., shape=[common.num_classes]), name="b")

    # Doing the affine projection(做仿射投影) 这个就是lstm_ctc要的最终结果[time_step,num_class]=[64*256,12]
    logits = tf.matmul(outputs, W) + b

    # Reshaping back to the original shape
    logits = tf.reshape(logits, [batch_s, -1, common.num_classes])

    # Time major
    logits = tf.transpose(logits,
                          (1, 0,
                           2))  # transpose (1, 0, 2)理解，本来的第一维，第二维，第三维的顺序是（0，1，2），现在写成（1，0，2）说明是第一维和第二维交换一下位置，第三维还在原来的位置保持不变

    return logits, inputs, targets, seq_len, W, b


if __name__ == '__main__':
    logits, inputs, targets, seq_len, W, b = get_train_model()
