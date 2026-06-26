<?php
// setup before dispatch
$action = $_GET['action'] ?? null;

class data_sanitiser {
    public const MODE = 'strict';
    private string $name = 'default';

    public function sanitise_data($value) {
        $normalised = function () use ($value) {
            return trim($value);
        };
        $items = array_map(fn($item) => trim($item), [$normalised()]);
        if ($items) {
            return $items[0];
        }
        return null;
    }

    public static function create_instance(): self {
        try {
            return new self();
        } catch (Exception $exception) {
            throw $exception;
        }
    }

    public function __construct() {
        $this->name = 'ready';
    }
}

trait my_trait {
    public function apply() {
        return true;
    }
}

interface webhook_auth {
    public function authorise_request();
    public function with_body(): bool {
        return true;
    }
}

enum WebhookStatus {
    case Ready;

    public function label(): string {
        return match ($this) {
            self::Ready => 'ready',
        };
    }
}

function handle_webhook_error() {
    function inner_helper() {
        return true;
    }
    return inner_helper();
}

switch ($action) {
    case 'delete':
        delete_user();
        break;
    case 'create':
        create_user();
        break;
}

if ($action === 'archive') {
    archive_user();
}

$after_dispatch = true;
